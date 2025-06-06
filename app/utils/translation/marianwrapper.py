from app import app
from app.utils import utils
import tempfile
import subprocess
import os
import yaml


class MarianWrapper:
    def __init__(self, engine_path, finetuned, opus_engine, src_lang_3, trg_lang_3):
        try:
            # for inference the model specified in the decoder.yml should be used
            self.model = os.path.join(engine_path, "model.npz.decoder.yml")
            self.finetuned = finetuned
            self.opus_engine = opus_engine
            self.src_lang_3 = src_lang_3
            self.trg_lang_3 = trg_lang_3

        except Exception as ex:
            print("Exception in MarianWrapper init ----")
            print(ex, flush = True)

    def translate(self, lines, n_best=False, engine_path = None, use_opus_way = False):
        translations = []
        output_tmp = tempfile.NamedTemporaryFile(delete=False)
        n_best_flag = "--n-best" if n_best else ""
        input_tmp = tempfile.NamedTemporaryFile(delete=False)
        lines = [line.rstrip("\n") + "\n" for line in lines]

        # if this is a multilingual finetuned model that comes from OPUS
        # we have to manually set the target language via a token
        MULTILANG_CONCAT = ""
        if self.finetuned or self.opus_engine:
        #    lines = [f">>{self.trg_lang_3}<< " + line for line in lines]
            MULTILANG_CONCAT = f"| sed 's/^/>>{self.trg_lang_3}<< /'"

        with open(input_tmp.name, "w") as f:
            f.writelines(lines)

        if use_opus_way:
            # preprocess.sh spmodel cmake_dir < input > output
            preprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_preprocess.sh")
            postprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_postprocess.sh")
            spm_model_path = os.path.join(engine_path, 'source.spm')
            spm_script_path = os.path.join(app.config["MARIAN_FOLDER"], "build/spm_encode")

            marian_opus_cmd = "cat {0} | {1} {2} {3} {4} | {5}/build/marian-decoder -c {6} {7} -w 4000 | {8} > {9}".format(
                    input_tmp.name, 
                    preprocess_script_path, 
                    spm_model_path, 
                    spm_script_path, 
                    MULTILANG_CONCAT,
                    app.config["MARIAN_FOLDER"], 
                    self.model,
                    n_best_flag,
                    postprocess_script_path,
                    output_tmp.name)
            
            print("______________________________", flush = True)
            print("TRANSLATING LINE WITH COMMAND:", flush = True)
            print(marian_opus_cmd, flush = True)
            print("______________________________", flush = True)

            marian_opus_cmd_proc = subprocess.run(marian_opus_cmd, cwd=utils.filepath('TMP_FOLDER'), shell=True, capture_output=True)

            if marian_opus_cmd_proc.returncode != 0:
                print("- OPUS TRANSLATION ERROR:", flush = True)
                print(marian_opus_cmd_proc.stderr, flush = True)
                print("--------", flush = True)
                raise Exception
        else:
            marian_cmd = (
                "cat {0} {1} | {2}/build/marian-decoder -c {3} {4} -w 4000 > {5}".format(
                    input_tmp.name,
                    MULTILANG_CONCAT,
                    app.config["MARIAN_FOLDER"],
                    self.model,
                    n_best_flag,
                    output_tmp.name,
                )
            )

            print("______________________________", flush = True)
            print("TRANSLATING LINE WITH COMMAND:", flush = True)
            print(marian_cmd, flush = True)
            print("______________________________", flush = True)

            try:
                subprocess.run(marian_cmd, shell=True, capture_output=True, check=True)
            except Exception as e:
                raise Exception from e
        
        with open(output_tmp.name, "r") as temp_file:
            translations = [line.rstrip("\n") for line in temp_file.readlines()]
        
        os.remove(input_tmp.name)
        os.remove(output_tmp.name)

        return translations

    def translate_file(self, input_path, output_path, n_best = False, engine_path = None, use_opus_way = False):
        n_best_flag = "--n-best" if n_best else ""

        # if this is a multilingual finetuned model that comes from OPUS
        # we have to manually set the target language via a token
        MULTILANG_CONCAT = ""
        if self.finetuned or self.opus_engine:
            MULTILANG_CONCAT = f"| sed 's/^/>>{self.trg_lang_3}<< /'"

        if use_opus_way:
            # preprocess.sh spmodel cmake_dir < input > output
            preprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_preprocess.sh")
            postprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_postprocess.sh")
            spm_model_path = os.path.join(engine_path, 'source.spm')
            spm_script_path = os.path.join(app.config["MARIAN_FOLDER"], "build/spm_encode")

            marian_opus_cmd = "cat {0} | {1} {2} {3} {4} | {5}/build/marian-decoder -c {6} {7} -w 4000 | {8} > {9}".format(
                    input_path, 
                    preprocess_script_path, 
                    spm_model_path, 
                    spm_script_path, 
                    MULTILANG_CONCAT, 
                    app.config["MARIAN_FOLDER"], 
                    self.model,
                    n_best_flag,
                    postprocess_script_path,
                    output_path)
            
            print("______________________________", flush = True)
            print("TRANSLATING FILE WITH COMMAND:", flush = True)
            print(marian_opus_cmd, flush = True)
            print("______________________________", flush = True)

            marian_opus_cmd_proc = subprocess.run(marian_opus_cmd, cwd=utils.filepath('TMP_FOLDER'), shell=True, capture_output=True)

            if marian_opus_cmd_proc.returncode != 0:
                print("- OPUS TRANSLATION ERROR:", flush = True)
                print(marian_opus_cmd_proc.stderr, flush = True)
                print("--------", flush = True)
                raise Exception

        else:
            marian_cmd = (
                "cat {0} {1} | {2}/build/marian-decoder -c {3} {4} -w 4000 > {5}".format(
                    input_path,
                    MULTILANG_CONCAT,
                    app.config["MARIAN_FOLDER"],
                    self.model,
                    n_best_flag,
                    output_path,
                )
            )

            print("______________________________", flush = True)
            print("TRANSLATING FILE WITH COMMAND:", flush = True)
            print(marian_cmd, flush = True)
            print("______________________________", flush = True)

            try:
                subprocess.run(marian_cmd, shell=True, capture_output=True, check=True)
            except Exception as e:
                print(e, flush = True)
                return False

        return True
