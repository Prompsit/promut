from app import app
from app.blueprints.evaluate.evaluator import Evaluator

import subprocess

class Comet(Evaluator):
    def get_name(self):
        return "Comet"

    def get_value(self, mt_path, ht_path, source_path = ""):
        # If source path is specified, then create the parameter call for pymarian-eval
        if source_path != "":
            src_path = "-s {0}".format(source_path)

        #print("--- COMMAND:", flush = True)
        #print("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} --average only".format(mt_path, src_path, ht_path))
        #print("-------", flush = True)

        comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} --average only".format(mt_path, src_path, ht_path), 
                        shell=True, stdout=subprocess.PIPE)

        # UNCOMMENT FOR CPU COMET !!!
        #comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} --average only -c 8".format(mt_path, src_path, ht_path), 
        #                shell=True, stdout=subprocess.PIPE)

        score = comet.stdout.decode("utf-8").strip()

        return 0, float(score), 1