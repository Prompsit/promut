from app import app
from app.utils import utils
import tempfile
import subprocess
import os


class MarianWrapper:
    def __init__(self, engine_path):
        self.model = str(engine_path) + "/model.npz.best-bleu.npz.decoder.yml"

    def translate(self, lines, n_best=False, engine_path = None, use_opus_way = False):
        translations = []
        output_tmp = tempfile.NamedTemporaryFile(delete=False)
        n_best_flag = "--n-best" if n_best else ""
        input_tmp = tempfile.NamedTemporaryFile(delete=False)
        lines = [line.rstrip("\n") + "\n" for line in lines]
        with open(input_tmp.name, "w") as f:
            f.writelines(lines)

        if use_opus_way:
            # preprocess.sh spmodel cmake_dir < input > output
            preprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_preprocess.sh")
            postprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_postprocess.sh")
            spm_model_path = os.path.join(engine_path, 'source.spm')
            spm_script_path = os.path.join(app.config["MARIAN_FOLDER"], "build/spm_encode")

            marian_opus_cmd = "cat {0} | {1} {2} {3} | {4}/build/marian-decoder -c {5} {6} -w 4000 | {7} > {8}".format(
                    input_tmp.name, 
                    preprocess_script_path, 
                    spm_model_path, 
                    spm_script_path, 
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
                "cat {0} | {1}/build/marian-decoder -c {2} {3} -w 4000 > {4}".format(
                    input_tmp.name,
                    app.config["MARIAN_FOLDER"],
                    self.model,
                    n_best_flag,
                    output_tmp.name,
                )
            )

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

        if use_opus_way:
            # preprocess.sh spmodel cmake_dir < input > output
            preprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_preprocess.sh")
            postprocess_script_path = os.path.join(app.config["BASE_CONFIG_FOLDER"], "opus_postprocess.sh")
            spm_model_path = os.path.join(engine_path, 'source.spm')
            spm_script_path = os.path.join(app.config["MARIAN_FOLDER"], "build/spm_encode")

            marian_opus_cmd = "cat {0} | {1} {2} {3} | {4}/build/marian-decoder -c {5} {6} -w 4000 | {7} > {8}".format(
                    input_path, 
                    preprocess_script_path, 
                    spm_model_path, 
                    spm_script_path, 
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
                "{0}/build/marian-decoder -c {1} {2} -i {3} -o {4} -w 4000 --mini-batch 16".format(
                    app.config["MARIAN_FOLDER"],
                    self.model,
                    n_best_flag,
                    input_path,
                    output_path,
                )
            )

            try:
                subprocess.run(marian_cmd, shell=True, capture_output=True, check=True)
            except Exception as e:
                print(e, flush = True)
                return False

        return True
