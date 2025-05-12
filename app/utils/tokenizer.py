from app import app
from app.utils import utils
import sentencepiece as spm
import tempfile
import os
import subprocess

class Tokenizer:
    def __init__(self, engine, use_opus_way = False):
        self.sp = None
        self.loaded = False
        self.path = engine.path
        self.src_lang = engine.source.code 
        self.trg_lang = engine.target.code

    def load(self):
        if not self.sp:
            model_file = os.path.join(self.path, f"vocab.{self.src_lang}{self.trg_lang}.spm")
            self.sp = spm.SentencePieceProcessor(model_file=model_file)
            
    def tokenize(self, text, use_opus_way = False):
        if use_opus_way:
            input_tmp = tempfile.NamedTemporaryFile(delete=False)
            text = [t.rstrip("\n") + "\n" for t in text]
            with open(input_tmp.name, "w") as f:
                f.writelines(text)

            # preprocess.sh spmodel cmake_dir < input > output
            preprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_preprocess.sh")
            spm_model_path = os.path.join(self.path, 'source.spm')
            spm_script_path = os.path.join(app.config["MARIAN_FOLDER"], "build/spm_encode")
            
            preprocess_cmd = "{0} {1} {2} < {3}".format(preprocess_script_path, spm_model_path, spm_script_path, input_tmp.name)
            preprocessing_proc = subprocess.run(preprocess_cmd, cwd=utils.filepath('TMP_FOLDER'), shell=True, capture_output=True)

            if preprocessing_proc.returncode != 0:
                print("- SPM TOKENIZATION ERROR:", flush = True)
                print(preprocessing_proc.stderr, flush = True)
                print("--------", flush = True)
                raise Exception
            
            os.remove(input_tmp.name)
            return preprocessing_proc.stdout.decode('utf-8')
        else:
            if self.sp:
                return " ".join(self.sp.encode(text, out_type=str))
        return None