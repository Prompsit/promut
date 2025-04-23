from app import app, db
from app.blueprints.evaluate.evaluator import Evaluator
from app.utils.GPUManager import GPUManager
from app.utils import user_utils

import subprocess

class Comet(Evaluator):
    def get_name(self):
        return "Comet"

    def get_value(self, mt_path, ht_path, source_path = ""):
        # If source path is specified, then create the parameter call for pymarian-eval
        if source_path != "":
            src_path = "-s {0}".format(source_path)
        
        with app.app_context():
            # for commet calculation, check first if there is an available GPU
            # if not, then use CPU to calculate it, though it will take a lot longer
            gpu_id = GPUManager.get_available_device()
            if gpu_id is not None:
                device_command = f"-d {gpu_id}"
                print("AAAAAAAAAAAAAAAA", flush = True)
                try:
                    comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} --average only {3} --workspace 6000".format(mt_path, src_path, ht_path, device_command), 
                                            shell=True, capture_output=True)

                    if comet.returncode != 0:
                        print("ERROR WITH GPU:", flush = True)
                        print(comet.stderr, flush = True)
                    else:
                        print("NOTHING HAPPENED", flush = True)
                except Exception as e:
                    print(e, flush = True)

                GPUManager.free_device(gpu_id)
                db.session.commit()
            else:
                comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} --average only -c 8".format(mt_path, src_path, ht_path), 
                                        shell=True, stdout=subprocess.PIPE)
        
        score = comet.stdout.decode("utf-8").strip()

        return 0, float(score), 1