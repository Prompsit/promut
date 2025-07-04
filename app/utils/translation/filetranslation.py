from app import app
from app.models import Engine, RunningEngines, User
from app.utils import utils

from lxml import etree
from nltk.tokenize import sent_tokenize

import zipfile
import os
import re
import shutil
import glob
import subprocess

class FileTranslation:
    def __init__(self, translator, engine_path = None):
        self.format_mappings = {
            ".pptx": r'.*(slide(s*))$',
            ".docx": r'.*(document.xml)$',
            ".xlsx": r'.*sharedStrings\.xml$',
            ".libreoffice": r'.*content\.xml$'
        }
        
        self.format_filters = {
            ".pdf": "docx",
            ".rtf": "docx"
        }

        self.sentences = {}

        self.translator = translator
        self.engine_path = engine_path

    def norm_extension(self, extension):
        if extension in [".ppt", ".doc", ".xls"]:
            return extension + "x"
        elif extension in [".odp", ".odt", ".ods", ".odg"]:
            return ".libreoffice"
        else:
            return extension

    def line(self, text):
        if text.strip() != "":
            # line_tok = self.tokenizer.tokenize(text)
            line = self.translator.translate([text], engine_path = self.engine_path, use_opus_way = True)
            return line[0]
            # return self.tokenizer.detokenize(translation)
        else:
            return ""

    def translate_txt(self, user_id, file_path, as_tmx = False):

        try:
            translated_path = '{}.translated'.format(file_path)
            
            # translate the whole freaking file
            self.translator.translate_file(file_path, translated_path, n_best = False, engine_path = self.engine_path, use_opus_way = True)

            # write source and target lines to tmx if it's wanted
            with open(file_path, 'r') as source, open(translated_path, 'r') as target:
                for source_line, target_line in zip(source, target):
                    if as_tmx: self.sentences[str(user_id)].append({ "source": source_line.strip(), "target": [target_line.strip()] })

            os.remove(file_path)
            shutil.move(translated_path, file_path)

        except Exception as ex:
            raise Exception from ex

    def translate_xml(self, user_id, xml_path, mode = "xml", as_tmx = False):
        office = (mode == "office")
        mode = "xml" if mode == "office" else mode

        def explore_node(node):
            if node.text and node.text.strip():
                if not office or (office and node.tag in ["{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t", "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p"]):
                    translation = self.line(node.text)
                    if as_tmx: self.sentences[str(user_id)].append({ "source": node.text, "target": [translation] })
                    node.text = translation
            for child in node:
                explore_node(child)
        
        with open(xml_path, 'r') as xml_file:
            parser = etree.HTMLParser() if mode == "html" else etree.XMLParser()
            tree = etree.parse(xml_file, parser)
            explore_node(tree.getroot())

        tree.write(xml_path, encoding="UTF-8", xml_declaration=(mode == "xml"))

    def translate_tmx(self, user_id, tmx_path, tmx_mode):
        sentences = []

        with open(tmx_path, 'r') as xml_file:
            tmx = etree.parse(xml_file, etree.XMLParser())
            body = tmx.getroot().find("body")
            for tu in body.findall('.//tu'):
                sentence = None

                for i, tuv in enumerate(tu.findall('.//tuv')):
                    text = tuv.find("seg").text
                    if i == 0:
                        sentence = { "source": text, "target": [] }
                    else:
                        if tmx_mode == "create":
                            sentence.get('target').append(text)
                        sentence.get('target').append(self.line(text))

                sentences.append(sentence)
            
        tmx_path_translated = self.tmx_builder(user_id, sentences)
        shutil.move(tmx_path_translated, tmx_path)

    def translate_office(self, user_id, file_path, as_tmx = False):
        filename, extension = os.path.splitext(file_path)
        norm_extension = self.norm_extension(extension)

        if norm_extension in self.format_mappings.keys():
            extract_path = '{}-extract'.format(filename)
            os.mkdir(extract_path)

            with zipfile.ZipFile(file_path, 'r') as zip:
                zip.extractall(extract_path)

            os.remove(file_path)

            for xml_file_path in [f for f in glob.glob(os.path.join(extract_path, "**/*.xml"), recursive=True)]:
                if re.search(self.format_mappings[norm_extension], xml_file_path):
                    self.translate_xml(user_id, xml_file_path, "office", as_tmx)
            
            shutil.make_archive(filename, 'zip', extract_path, '.')
            shutil.move('{}.zip'.format(filename), file_path)
            shutil.rmtree(extract_path)

    def translate_bridge(self, user_id, file_path, original_extension, as_tmx = False):
        dest_format = self.format_filters[original_extension]
        filename, extension = os.path.splitext(file_path)
        dest_path = filename + "." + dest_format

        if original_extension == ".pdf":
            convert = subprocess.Popen("soffice --convert-to doc {} --outdir {} --infilter=\"writer_pdf_import\"".format(file_path, os.path.dirname(dest_path)),
                            shell=True, cwd=app.config['MUTNMT_FOLDER'], 
                            stdout=subprocess.PIPE)
            convert.wait()

            convert = subprocess.Popen("soffice --convert-to {} {}.doc --outdir {}".format(dest_format,
                            filename, os.path.dirname(dest_path)), shell=True, cwd=app.config['MUTNMT_FOLDER'], 
                            stdout=subprocess.PIPE)
            convert.wait()
        else:
            convert = subprocess.Popen("soffice --convert-to {} {} --outdir {} --infilter=\"writer_pdf_import\"".format(dest_format,
                    file_path, os.path.dirname(dest_path)), shell=True, cwd=app.config['MUTNMT_FOLDER'], 
                    stdout=subprocess.PIPE)
            convert.wait()

        self.translate_office(user_id, dest_path, as_tmx)

        convert = subprocess.Popen("soffice --convert-to {} {} --outdir {}".format(original_extension[1:], dest_path,
                                os.path.dirname(dest_path)), shell=True, cwd=app.config['MUTNMT_FOLDER'], stdout=subprocess.PIPE)
        convert.wait()

        os.remove(dest_path)

    def tmx_builder(self, user_id, sentences):
        with app.app_context():
            engine = RunningEngines.query.filter_by(user_id=user_id).first().engine
            source_lang = engine.source.code
            target_lang = engine.target.code

            with open(os.path.join(app.config['BASE_CONFIG_FOLDER'], 'base.tmx'), 'r') as tmx_file:
                tmx = etree.parse(tmx_file, etree.XMLParser())
                body = tmx.getroot().find("body")
                for sentence in sentences:
                    tu = etree.Element("tu")

                    tuv_source = etree.Element("tuv", { etree.QName("http://www.w3.org/XML/1998/namespace", "lang"): source_lang })
                    seg_source = etree.Element("seg")
                    seg_source.text = sentence.get('source')
                    tuv_source.append(seg_source)
                    tu.append(tuv_source)

                    for target_sentence in sentence.get('target'):
                        tuv_target = etree.Element("tuv", { etree.QName("http://www.w3.org/XML/1998/namespace", "lang"): target_lang })
                        seg_target = etree.Element("seg")
                        seg_target.text = target_sentence
                        tuv_target.append(seg_target)
                        tu.append(tuv_target)

                    body.append(tu)

            tmx_path = utils.tmpfile('{}.{}-{}.tmx'.format(user_id, engine.source.code, engine.target.code))
            tmx.write(tmx_path, encoding="UTF-8", xml_declaration=True)

            format_proc = subprocess.Popen("xmllint --format {} > {}.format".format(tmx_path, tmx_path), shell=True)
            format_proc.wait()

            shutil.move("{}.format".format(tmx_path), tmx_path)

            return tmx_path

    def text_as_tmx(self, user_id, text):
        sentences = []
        for line in text:
            raw_sentences = sent_tokenize(line)
            for sentence in raw_sentences:
                sentences.append({ "source": sentence, "target": [self.line(sentence)] })
        return self.tmx_builder(user_id, sentences)

    def translate_file(self, user_id, file_path, as_tmx, tmx_mode):
        filename, extension = os.path.splitext(file_path)
        self.sentences[str(user_id)] = [] if as_tmx else None
        
        if extension in [".xml", ".html"]:
            self.translate_xml(user_id, file_path, extension[1:], as_tmx)
        elif extension == ".tmx":
            self.translate_tmx(user_id, file_path, tmx_mode)
        elif extension == ".txt":
            self.translate_txt(user_id, file_path, as_tmx)
        elif extension in [".rtf", ".pdf"]:
            self.translate_bridge(user_id, file_path, extension, as_tmx)
        else:
            self.translate_office(user_id, file_path, as_tmx)
        with app.app_context():
            engine = RunningEngines.query.filter_by(user_id=user_id).first()
            file_path_translated = '{}.{}-{}{}'.format(filename, engine.engine.source.code, engine.engine.target.code, extension)
            shutil.move(file_path, file_path_translated)
            file_path = file_path_translated

            if as_tmx:
                tmx_path = self.tmx_builder(user_id, self.sentences[str(user_id)])

                bundle_path = '{}-tmx-bundle'.format(filename)
                os.mkdir(bundle_path)

                filename, extension = os.path.splitext(file_path)
                basename = os.path.basename(filename)
                shutil.move(tmx_path, os.path.join(bundle_path, '{}.tmx'.format(basename)))
                shutil.move(file_path, os.path.join(bundle_path, '{}{}'.format(basename, extension)))
                shutil.make_archive(filename, 'zip', bundle_path, '.')
                shutil.rmtree(bundle_path)

                return filename + '.zip'

        return file_path
