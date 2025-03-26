from app import app
import tempfile
import subprocess
import os


class MarianWrapper:
    def __init__(self, engine_path):
        self.model = str(engine_path) + "/model.npz.best-bleu.npz.decoder.yml"

    def translate(self, lines, n_best=False):
        translations = []
        output_tmp = tempfile.NamedTemporaryFile(delete=False)
        n_best_flag = "--n-best" if n_best else ""
        input_tmp = tempfile.NamedTemporaryFile(delete=False)
        lines = [line.rstrip("\n") + "\n" for line in lines]
        with open(input_tmp.name, "w") as f:
            f.writelines(lines)

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

    def translate_file(self, input_path, output_path, n_best = False):
        n_best_flag = "--n-best" if n_best else ""

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
