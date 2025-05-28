import datetime
import importlib
import inspect
import json
import logging
import os
import pkgutil
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.parsers.expat

import pyter
import redis
import xlsxwriter
import yaml
from celery import Celery
from celery.signals import task_postrun, task_prerun
from flask import url_for
from flask_login import current_user
from nltk.tokenize import sent_tokenize
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import app, db
from app.flash import Flash
from app.models import (
    Corpus,
    Corpus_Engine,
    Corpus_File,
    Engine,
    LibraryCorpora,
    LibraryEngine,
    RunningEngines,
    User,
    UserLanguage,
)
from app.utils import data_utils, ttr, user_utils, utils
from app.utils.GPUManager import GPUManager
from app.utils.power import PowerUtils
from app.utils.roles import EnumRoles
from app.utils.tokenizer import Tokenizer
from app.utils.trainer import Trainer
from app.utils.translation.filetranslation import FileTranslation
from app.utils.translation.marianwrapper import MarianWrapper
from app.utils.translation.utils import TranslationUtils

celery = Celery(app.name, broker = app.config["CELERY_BROKER_URL"], backend = app.config["CELERY_RESULT_BACKEND"])
celery.conf.update(app.config)

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Engine training tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
def join_corpora(list_name, phase, source_lang, target_lang, engine_id, user_id, used_corpora, params):
    with app.app_context():
        corpus = Corpus(owner_id=user_id, visible=False)
        for train_corpus in params[list_name]:
            corpus_data = json.loads(train_corpus)
            corpus_id = corpus_data["id"]
            corpus_size = corpus_data["size"]

            if corpus_id not in used_corpora:
                used_corpora[corpus_id] = 0

            try:
                og_corpus = Corpus.query.filter_by(id=corpus_id).first()

                # We relate the original corpus with this engine in the database,
                # for informational purposes. This way the user will be able to know
                # which corpora were used to train the engine
                engine = db.session.query(Engine).filter_by(id=engine_id).first()
                engine.engine_corpora.append(
                    Corpus_Engine(
                        corpus=og_corpus,
                        engine=engine,
                        phase=phase,
                        is_info=True,
                        selected_size=corpus_size,
                    )
                )

                corpus.user_source_id = og_corpus.user_source_id
                corpus.user_target_id = og_corpus.user_target_id
                for file_entry in og_corpus.corpus_files:
                    with open(file_entry.file.path, "rb") as file_d:
                        db_file = data_utils.upload_file(
                            FileStorage(
                                stream=file_d, filename=file_entry.file.name
                            ),
                            file_entry.file.user_language_id,
                            selected_size=corpus_size,
                            offset=used_corpora[corpus_id],
                            user_id=user_id,
                        )
                    corpus.corpus_files.append(
                        Corpus_File(
                            db_file,
                            role=(
                                "source"
                                if file_entry.file.language.code == source_lang
                                else "target"
                            ),
                        )
                    )
                used_corpora[corpus_id] += corpus_size
            except Exception as ex:
                print(ex, flush=True)
                raise ex

        try:
            db.session.add(corpus)
            db.session.commit()
        except:
            db.session.rollback()
            raise Exception

        # We put the contents of the several files in a new single one, and we shuffle the sentences
        try:
            data_utils.join_corpus_files(corpus, shuffle=True, user_id=user_id)
        except:
            db.session.delete(corpus)
            db.session.commit()
            raise Exception

        return corpus.id, used_corpora

def link_files(corpus, engine, phase, config, params):
    try:
        sets_arr = []
        for file_entry in corpus.corpus_files:
            # create split filename and create path to it
            split_name = "{}.{}".format(
                phase,
                (
                    params["source_lang"]
                    if file_entry.role == "source"
                    else params["target_lang"]
                ),
            )

            # link raw corpus path to raw split path
            corpus_path_raw = file_entry.file.path
            split_path_raw = str(os.path.join(engine.path, split_name)) + ".raw"
            os.link(corpus_path_raw, split_path_raw)

            # link preprocessed corpus path to preprocessed split path
            corpus_path_pre = file_entry.file.path + ".mut.spe"
            split_path_pre = str(os.path.join(engine.path, split_name))
            os.link(corpus_path_pre, split_path_pre)

            sets_arr.append(split_path_pre)

        # insert it to configs in Marian style for train and valid sets, e.g. "train-sets" array
        if phase != "test":
            set_name = f"{phase}-sets"
            config[set_name] = sets_arr
        
        return config

    except Exception as ex:
        logging.exception("An exception was thrown in LINK FILES")

@celery.task(bind=True)
def launch_training(self, user_id, engine_path, params):
    try:
        with app.app_context():
            # Performs necessary steps to configure an engine and get it ready for training

            engine = Engine(path=engine_path)
            engine.uploader_id = user_id
            engine.status = "launching"
            engine.bg_task_id = self.request.id

            db.session.add(engine)
            db.session.commit()

            used_corpora = {}

            try:
                os.makedirs(engine_path)
            except:
                Flash.issue("The engine could not be created", Flash.ERROR)
                return url_for("train.train_index", id=id)

            train_corpus_id, used_corpora = join_corpora(
                "training[]",
                phase="train",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
                user_id=user_id,
                used_corpora=used_corpora,
                params=params
            )
            dev_corpus_id, used_corpora = join_corpora(
                "dev[]",
                phase="dev",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
                user_id=user_id,
                used_corpora=used_corpora,
                params=params
            )
            test_corpus_id, used_corpora = join_corpora(
                "test[]",
                phase="test",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
                user_id=user_id,
                used_corpora=used_corpora,
                params=params
            )

            train_corpus = db.session.query(Corpus).filter_by(id=train_corpus_id).first()
            dev_corpus = db.session.query(Corpus).filter_by(id=dev_corpus_id).first()
            test_corpus = db.session.query(Corpus).filter_by(id=test_corpus_id).first()

            # We train a SentencePiece model to be used when OPUS handling way is wanted
            if app.config['USE_OPUS_HANDLING']:
                _, _, tokenizer_src_path = data_utils.train_tokenizer(engine, train_corpus_id, params["source_lang"], params["target_lang"], params['vocabularySize'])

            engine.name = params["nameText"]
            engine.description = params["descriptionText"]

            # set engine model path and create the folder so Marian can use it
            engine.model_path = os.path.join(engine.path, "model")
            os.mkdir(engine.model_path)

            source_lang = UserLanguage.query.filter_by(
                code=params["source_lang"], user_id=user_id
            ).one()
            engine.user_source_id = source_lang.id

            target_lang = UserLanguage.query.filter_by(
                code=params["target_lang"], user_id=user_id
            ).one()
            engine.user_target_id = target_lang.id

            engine.engine_corpora.append(
                Corpus_Engine(corpus=train_corpus, engine=engine, phase="train")
            )
            engine.engine_corpora.append(
                Corpus_Engine(corpus=dev_corpus, engine=engine, phase="dev")
            )
            engine.engine_corpora.append(
                Corpus_Engine(corpus=test_corpus, engine=engine, phase="test")
            )

            engine.status = "training_pending"
            engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)

            # user = db.session.query(User).filter_by(id=user_id).first()
            user = User.query.filter_by(id=user_id).first()
            user.user_engines.append(LibraryEngine(engine=engine, user=user))

            config_file_path = os.path.join(engine.path, "config.yaml")

            # get Marian engine configuration
            shutil.copyfile(
                os.path.join(
                    app.config["BASE_CONFIG_FOLDER"], "transformer-marian.yaml"
                ),
                config_file_path,
            )

            db.session.add(engine)
            db.session.commit()

            config = None

            try:
                with open(config_file_path, "r") as config_file:
                    config = yaml.load(config_file, Loader=yaml.FullLoader)
            except:
                raise Exception

            data_utils.tokenize(train_corpus_id, engine, use_opus_way = app.config['USE_OPUS_HANDLING'])
            data_utils.tokenize(dev_corpus_id, engine, use_opus_way = app.config['USE_OPUS_HANDLING'])
            data_utils.tokenize(test_corpus_id, engine, use_opus_way = app.config['USE_OPUS_HANDLING'])

            # link set files and insert in config file
            link_files(corpus=train_corpus, engine=engine, phase="train", config=config, params=params)
            link_files(corpus=dev_corpus, engine=engine, phase="valid", config=config, params=params)
            link_files(corpus=test_corpus, engine=engine, phase="test", config=config, params=params)

            ######################################################################################################
            # use these paths if normal vocabulary files is wanted, no tokenization 
            # call marian-vocab to create vocabulary files
            src_vocab_path, trg_vocab_path = data_utils.marian_vocab(
                engine,
                params["source_lang"],
                params["target_lang"],
                params["vocabularySize"],
                use_opus_way = app.config['USE_OPUS_HANDLING']
            )
            
            # use these paths if only sentencepiece model is wanted and OPUS handling is set to False
            if not app.config['USE_OPUS_HANDLING']:
                src_vocab_path = f"vocab.{params['source_lang']}{params['target_lang']}.spm"
                trg_vocab_path = f"vocab.{params['source_lang']}{params['target_lang']}.spm"
            ######################################################################################################

            # set vocabulary paths and dimensions
            # if no OPUS handling is wanted, then marian can automatically train 
            # a sentencepiece model if .spm files are specified here
            src_vocab = os.path.join(
                engine.path, src_vocab_path
            )
            trg_vocab = os.path.join(
                engine.path, trg_vocab_path
            )
            config["vocabs"] = [src_vocab, trg_vocab]
            config["dim-vocabs"] = [params["vocabularySize"], params["vocabularySize"]]

            # set paths to model files and to training log
            config["model"] = os.path.join(engine.path, "model/model.npz")
            config["log"] = os.path.join(engine.path, "model/train.log")

            # set user values for epochs, early stopping patience and validation frequency
            config["after"] = f"{params['epochsText']}e"
            config["early-stopping"] = int(params["patienceTxt"])
            config["valid-freq"] = int(params["validationFreq"])

            config["mini-batch"] = int(params['batchSizeTxt'])
            config["beam-size"] = int(params['beamSizeTxt'])

            with open(config_file_path, "w") as config_file:
                yaml.dump(config, config_file)

            engine.status = "ready"
            engine.bg_task_id = None
            db.session.commit()

            return engine.id
    except Exception as ex:
        logging.exception("An exception was thrown in LAUNCH_TRAINING function!")
        print(ex, flush = True)
        with app.app_context():
            db.session.delete(engine)
            db.session.commit()

            if os.path.exists(engine_path) and os.path.isdir(engine_path):
                shutil.rmtree(engine_path)

            # Flash.issue("The engine could not be configured", Flash.ERROR)
            return -1

@celery.task(bind=True)
def launch_finetuning(self, user_id, engine_path, params):
    try:
        with app.app_context():
            # Performs necessary steps to configure an engine and get it ready for finetuning

            engine = Engine(path=engine_path)

            engine.uploader_id = user_id
            engine.status = "launching"
            engine.bg_task_id = self.request.id
            engine.name = params["nameText"]
            engine.description = params["descriptionText"] + " - Finetuned from model: " + params["engine_name"]
            engine.finetuned = True

            db.session.add(engine)
            db.session.commit()

            used_corpora = {}

            try:
                os.makedirs(engine_path)
            except:
                Flash.issue("The engine could not be created", Flash.ERROR)
                return url_for("train.train_index", id=id)

            # set engine model path and create the folder so Marian can use it
            engine.model_path = os.path.join(engine.path, "model")
            os.mkdir(engine.model_path)

            # copy all the necessary opus files into engine.path and engine.model_path
            opus_engine = Engine.query.filter_by(id=params["opus_engine_id"]).first()

            shutil.copy(os.path.join(opus_engine.path, "source.spm"), engine.path)
            shutil.copy(os.path.join(opus_engine.path, "target.spm"), engine.path)

            shutil.copy(os.path.join(opus_engine.model_path, "model.npz"), engine.model_path)
            shutil.copy(os.path.join(opus_engine.model_path, "model.npz.decoder.yml"), engine.model_path)

            # prepare corpora and data sets
            train_corpus_id, used_corpora = join_corpora(
                "training[]",
                phase="train",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
                user_id=user_id,
                used_corpora=used_corpora,
                params=params
            )
            dev_corpus_id, used_corpora = join_corpora(
                "dev[]",
                phase="dev",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
                user_id=user_id,
                used_corpora=used_corpora,
                params=params
            )
            test_corpus_id, used_corpora = join_corpora(
                "test[]",
                phase="test",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
                user_id=user_id,
                used_corpora=used_corpora,
                params=params
            )

            train_corpus = db.session.query(Corpus).filter_by(id=train_corpus_id).first()
            dev_corpus = db.session.query(Corpus).filter_by(id=dev_corpus_id).first()
            test_corpus = db.session.query(Corpus).filter_by(id=test_corpus_id).first()

            source_lang = UserLanguage.query.filter_by(code=params["source_lang"], user_id=user_id).one()
            engine.user_source_id = source_lang.id

            target_lang = UserLanguage.query.filter_by(code=params["target_lang"], user_id=user_id).one()
            engine.user_target_id = target_lang.id

            # add data sets to the engine
            engine.engine_corpora.append(Corpus_Engine(corpus=train_corpus, engine=engine, phase="train"))
            engine.engine_corpora.append(Corpus_Engine(corpus=dev_corpus, engine=engine, phase="dev"))
            engine.engine_corpora.append(Corpus_Engine(corpus=test_corpus, engine=engine, phase="test"))

            engine.status = "training_pending"
            engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)

            # link the datasets and engine to the user
            user = User.query.filter_by(id=user_id).first()
            user.user_engines.append(LibraryEngine(engine=engine, user=user))

            db.session.add(engine)
            db.session.commit()

            # create config file for finetuning
            config = None
            config_file_path = os.path.join(engine.path, "config.yaml")

            # get base Marian finetuning configuration
            # the finetuning config follows the same steps as in normal training,
            # however beam-size and dim-vocabs (beam size, vocabulary dimensions) will
            # be specified from the OPUS model parameters if available
            # additionally, the options 'type' and 'task' and anything else related
            # to the model options is removed, so that these are taken from the OPUS model
            shutil.copyfile(os.path.join(app.config["BASE_CONFIG_FOLDER"], "transformer-marian-finetuning.yaml"), config_file_path)
            
            with open(config_file_path, "r") as config_file:
                config = yaml.load(config_file, Loader=yaml.FullLoader)
            
            # set the vocabulary size by default to 0 and beam size from model options
            # for vocab size just delete de parameter so Marian can use default/model values
            del params["vocabularySize"]
            
            with open(os.path.join(opus_engine.model_path, "model.npz.decoder.yml"), "r") as opus_config_file:
                opus_config = yaml.load(opus_config_file, Loader=yaml.FullLoader)
            params['beamSizeTxt'] = str(opus_config['beam-size'])

            # final preparation and tokenization of data sets
            data_utils.tokenize(train_corpus_id, engine, use_opus_way = app.config['USE_OPUS_HANDLING'])
            data_utils.tokenize(dev_corpus_id, engine, use_opus_way = app.config['USE_OPUS_HANDLING'])
            data_utils.tokenize(test_corpus_id, engine, use_opus_way = app.config['USE_OPUS_HANDLING'])

            # link data set files and insert in config file
            link_files(corpus=train_corpus, engine=engine, phase="train", config=config, params=params)
            link_files(corpus=dev_corpus, engine=engine, phase="valid", config=config, params=params)
            link_files(corpus=test_corpus, engine=engine, phase="test", config=config, params=params)
            
            ######################################################################################################
            # use these paths if normal vocabulary files is wanted, no tokenization 
            # call marian-vocab to create vocabulary files
            src_lang = params["source_lang"]
            trg_lang = params["target_lang"]

            src_vocab_path = f"vocab.{src_lang}.yml"
            trg_vocab_path = f"vocab.{trg_lang}.yml"
            opus_src_vocab_path = os.path.join(opus_engine.path, src_vocab_path)
            opus_trg_vocab_path = os.path.join(opus_engine.path, trg_vocab_path)

            shutil.copy(opus_src_vocab_path, engine.path)
            shutil.copy(opus_trg_vocab_path, engine.path)
            
            # use these paths if only sentencepiece model is wanted and OPUS handling is set to False
            if not app.config['USE_OPUS_HANDLING']:
                src_vocab_path = f"vocab.{params['source_lang']}{params['target_lang']}.spm"
                trg_vocab_path = f"vocab.{params['source_lang']}{params['target_lang']}.spm"
            ######################################################################################################

            # set vocabulary paths and dimensions
            # if no OPUS handling is wanted, then marian can automatically train
            # a sentencepiece model if .spm files are specified here
            src_vocab = os.path.join(engine.path, src_vocab_path)
            trg_vocab = os.path.join(engine.path, trg_vocab_path)
            config["vocabs"] = [src_vocab, trg_vocab]

            # set paths to model files and to training log
            config["model"] = os.path.join(engine.path, "model/model.npz")
            config["log"] = os.path.join(engine.path, "model/train.log")

            # given that fresh OPUS models don't have a training log, we just create an empty
            # one so that no problems arise later in the code
            with open(config["log"], 'w') as file:
                pass
            
            # set user values for epochs, early stopping patience and validation frequency
            config["after"] = f"{params['epochsText']}e"
            config["early-stopping"] = int(params["patienceTxt"])
            config["valid-freq"] = int(params["validationFreq"])

            # mini-batch doesn't get used because of memory need,
            # instead mini-batch-fit is used directly from the config file
            #config["mini-batch"] = int(params['batchSizeTxt'])
            config["beam-size"] = int(params['beamSizeTxt'])

            with open(config_file_path, "w") as config_file:
                yaml.dump(config, config_file)

            engine.status = "ready"
            engine.bg_task_id = None
            db.session.commit()

            return engine.id

    except Exception as ex:
        with app.app_context():
            db.session.delete(engine)
            db.session.commit()

            if os.path.exists(engine_path) and os.path.isdir(engine_path):
                shutil.rmtree(engine_path)

            # Flash.issue("The engine could not be configured", Flash.ERROR)
            logging.exception("An exception was thrown in LAUNCH_FINETUNING function!")
            return -1

def add_graph_log(engine_model_path, engine_path):
    try:
        # log the newly created graph_dict.yaml into the graph_logs.yaml file
        dict_path = os.path.join(engine_model_path, "graph_dict.yaml")
        graph_log = os.path.join(engine_path, "graph_logs.yaml")

        if os.path.exists(graph_log):
            with open(graph_log, "r") as f:
                graphs_dict = yaml.load(f, Loader = yaml.FullLoader)

            new_index = max(graphs_dict.keys()) + 1
            graphs_dict[new_index] = dict_path

            with open(graph_log, "w") as f:
                yaml.dump(graphs_dict, f)
        else:
            graphs_dict = {}
            graphs_dict[1] = dict_path

            with open(graph_log, "w") as f:
                yaml.dump(graphs_dict, f)
    except:
        logging.exception("An exception was thrown in ADD_GRAPH_LOG!")

def refresh_full_graph_log(engine_path):
    try:
        # this function will be called throughout the training process to create
        # and update a log yaml file with all the relevant training values for graph drawing

        full_graph_log = os.path.join(engine_path, "full_graph.yaml")
        graph_log = os.path.join(engine_path, "graph_logs.yaml")

        # if graph logs yaml file does not exist, then just exit to not crash the functions
        if not os.path.exists(graph_log):
            return

        with open(graph_log, "r") as f:
            graph_paths = yaml.load(f, Loader = yaml.FullLoader)

        full_dict = {}
        first_log = True
        for graph_path in graph_paths.values():
            with open(graph_path, "r") as f:
                graph_dict = yaml.load(f, Loader = yaml.FullLoader)
            
            if first_log:
                full_dict = graph_dict
                first_log = False
            else:
                for key in graph_dict.keys():
                    if key != "train/train_epoch":
                        # get the final step in the current key
                        max_step = max([i["step"] for i in full_dict[key]])

                        for i, item in enumerate(graph_dict[key]):
                            # increment the current step by the amount of the final step in the key
                            # to have a realistic and gradual increase in training steps
                            graph_dict[key][i]["step"] = item["step"] + max_step

                        full_dict[key] += graph_dict[key]
                    else:
                        # if key is epochs, then just copy whatever is there
                        full_dict["train/train_epoch"] += graph_dict["train/train_epoch"]
                    
        with open(full_graph_log, "w") as f:
            yaml.dump(full_dict, f)
    except:
        logging.exception("An exception was thrown in REFRESH_FULL_GRAPH_LOG!")

@celery.task(bind=True)
def train_engine(self, engine_id, user_role, retrain_path=""):
    # Trains an engine by calling JoeyNMT and keeping
    # track of its progress
    try:
        with app.app_context():
            gpu_id = GPUManager.wait_for_available_device(is_admin=(user_role == EnumRoles.ADMIN))
            eng_path = ""

            try:
                engine = Engine.query.filter_by(id=engine_id).first()
                engine.status = "launching"
                engine.gid = gpu_id
                db.session.commit()

                eng_path = engine.path

                env = os.environ.copy()

                # set Marian pretrained path if the user wants to start training the model again
                marian_pretrained_cmd = ""
                if retrain_path != "" and os.path.exists(retrain_path):
                    marian_pretrained_cmd = f"--pretrained-model {retrain_path}"

                # get Marian training command and set available GPUs in environment
                config_path = os.path.join(engine.path, "config.yaml")
                marian_cmd = "{0}/build/marian -c {1} {2} --relative-paths".format(
                    app.config["MARIAN_FOLDER"], config_path, marian_pretrained_cmd
                )
                env["CUDA_VISIBLE_DEVICES"] = "{}".format(gpu_id)

                # run Marian training command
                # popen command must be run with shell functionality, and a process group must be created
                # with preexec_fn in order to be able to kill the process later with SIGTERM, else it won't stop
                marian_process = subprocess.Popen(marian_cmd, env=env, shell=True, preexec_fn = os.setsid)

                engine.status = "training"
                engine.pid = marian_process.pid
                db.session.commit()
                
                # add the graph log path to the logs file for historic use
                add_graph_log(engine.model_path, engine.path)

                # trainings are limited to 1 hour unless user has researcher or admin role
                start = datetime.datetime.now()
                difference = 0
                max_time = (
                    36000 # 10 hours
                    if (
                        user_role == EnumRoles.RESEARCHER
                        or user_role == EnumRoles.ADMIN
                    )
                    else 7200 # 2 hours
                )
                while difference < max_time:
                    time.sleep(10)
                    difference = (datetime.datetime.now() - start).total_seconds()
                    if marian_process.poll() is not None:
                        # training process finished (or died) before timeout
                        db.session.refresh(engine)
                        if (engine.status != "stopped" and engine.status != "stopped_admin"):
                            Trainer.stop(engine_id, calculate_elapsed = True)

                        GPUManager.free_device(gpu_id)
                        refresh_full_graph_log(eng_path)
                        db.session.remove()
                        return

                if marian_process.poll() is None:
                    refresh_full_graph_log(eng_path)
                    Trainer.stop(engine_id, calculate_elapsed = True)

            except Exception as ex:
                logging.exception("An exception was thrown in TRAIN_ENGINE!")
                logging.error("An exception was thrown in TRAIN_ENGINE!", exc_info=True)
                print(ex, flush = True)
            finally:
                engine.status = "stopped"
                GPUManager.free_device(gpu_id)
                db.session.commit()
                if eng_path != "":
                    refresh_full_graph_log(eng_path)
                db.session.remove()
    except Exception as ex:
        logging.exception("An exception was thrown in TRAIN_ENGINE!")
        db.session.remove()


@celery.task(bind=True)
def monitor_training(self, engine_id):
    redis_conn = redis.Redis()
    time.sleep(10)

    def monitor():
        try:
            with app.app_context():
                engine = Engine.query.filter_by(id=engine_id).first()
                if engine:
                    if not engine.has_stopped():
                        current_power = int(PowerUtils.get_mean_power(engine.gid))
                        power = redis_conn.hget("power_value", engine_id)
                        updates = redis_conn.hget("power_update", engine_id)

                        power = int(power) if power else 0
                        updates = int(updates) + 1 if updates else 1

                        redis_conn.hset("power_value", engine_id, power + current_power)
                        redis_conn.hset("power_update", engine_id, updates)
                        engine.power = int(power + current_power) / updates
                        db.session.commit()

                        time.sleep(12)
                        monitor()
                else:
                    time.sleep(30)
                    monitor()
        except Exception as ex:
            logging.exception("An exception was thrown in MONITOR!")

    monitor()


@celery.task(bind=True)
def test_training(self, engine_id):
    with app.app_context():
        try:
            engine = Engine.query.filter_by(id=engine_id).first()

            # get best BLEU model path
            model_path = os.path.join(engine.model_path, "model.npz.best-bleu.npz.decoder.yml")
            
            # get source and target test files, and create temporary file for
            test_source = os.path.join(engine.path, "test." + engine.source.code)
            _, test_source_preds = utils.tmpfile()
            test_target = os.path.join(engine.path, "test." + engine.target.code)

            # run marian decoder command to get predictions
            marian_cmd = (
                "{0}/build/marian-decoder -c {1} -i {2} -o {3} -w 4000".format(
                    app.config["MARIAN_FOLDER"],
                    model_path,
                    test_source,
                    test_source_preds,
                )
            )
            subprocess.run(marian_cmd, shell=True, capture_output=True, check=True)

            # get BLEU score from predictions and human translation
            sacre = subprocess.Popen("cat {} | sacrebleu -b {}".format(test_source_preds, test_target), 
                        cwd=app.config['MUTNMT_FOLDER'], shell=True, stdout=subprocess.PIPE)
            score = float(sacre.stdout.readline().decode("utf-8"))

            engine.test_task_id = None
            engine.test_score = score
            db.session.commit()

            return {"bleu": score}
        except Exception as e:
            db.session.rollback()
            raise e


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Translation tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


def launch_engine(user_id, engine_id):
    with app.app_context():
        user = User.query.filter_by(id=user_id).first()
        engine = Engine.query.filter_by(id=engine_id).first()
        
        # If this user is already using another engine, we switch
        user_engines = RunningEngines.query.filter_by(user_id=user_id).all()
        
        if user_engines:
            for user_engine in user_engines:
                db.session.delete(user_engine)
                db.session.commit()

        user.user_running_engines.append(RunningEngines(engine=engine, user=user))
        db.session.commit()
        translator = MarianWrapper(engine.model_path)

    return translator


@celery.task(bind=True)
def translate_text(self, user_id, engine_id, lines):
    translations = []
    with app.app_context():
        try:
            engine = Engine.query.filter_by(id=engine_id).first()
            translator = launch_engine(user_id, engine_id)

            translations = translator.translate(lines, engine_path = engine.path, use_opus_way = app.config['USE_OPUS_HANDLING'])

            db.session.delete(RunningEngines.query.filter_by(user_id=user_id).first())
            db.session.commit()
        except Exception as ex:
            print("Fails in translate_text", flush = True)
            print(str(ex), flush = True)
            db.session.rollback()
    return translations


@celery.task(bind=True)
def translate_file(self, user_id, engine_id, user_file_path, as_tmx, tmx_mode):
    with app.app_context():
        translator = launch_engine(user_id, engine_id)
        engine = Engine.query.filter_by(id=engine_id).first()
        file_translation = FileTranslation(translator, engine_path = engine.path)
        return file_translation.translate_file(user_id, user_file_path, as_tmx, tmx_mode)


@celery.task(bind=True)
def generate_tmx(self, user_id, engine_id, chain_engine_id, text):
    with app.app_context():
        engine = Engine.query.filter_by(id=engine_id).first()
        translator = launch_engine(user_id, engine_id)
        file_translation = FileTranslation(translator, engine_path = engine.path)

        if chain_engine_id:
            translations = []
            for line in text:
                if line.strip() != "":
                    for sentence in sent_tokenize(line):
                        translation = translator.translate(sentence, engine_path = engine.path, use_opus_way = app.config['USE_OPUS_HANDLING'])
                        translations.append(translation)
                else:
                    translations.append("")

            text = translations

        return file_translation.text_as_tmx(user_id, text)


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# INSPECT TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


@celery.task(bind=True)
def inspect_details(self, user_id, engine_id, line):
    translator = launch_engine(user_id, engine_id)
    with app.app_context():
        engine = Engine.query.filter_by(id=engine_id).first()
        tokenizer = Tokenizer(engine)
        inspect_details = None
        if line.strip() != "":
            use_opus_way = app.config['USE_OPUS_HANDLING']

            if use_opus_way:

                line_tok = tokenizer.tokenize(line, use_opus_way = use_opus_way)

                n_best = translator.translate([line], n_best=True, engine_path = engine.path, use_opus_way = use_opus_way)

                sentences = []
                for sent in n_best:
                    sentences.append(sent.split("|||")[1])
                del translator  # Free GPU slot

                inspect_details = {
                    "source": engine.source.code,
                    "target": engine.target.code,
                    "preproc_input": line_tok,
                    "preproc_output": tokenizer.tokenize(sentences[0], use_opus_way = use_opus_way),
                    "nbest": sentences,
                    "alignments": [],
                    "postproc_output": sentences[0],
                }

            else:
                tokenizer.load()
                line_tok = tokenizer.tokenize(line)
                n_best = translator.translate([line], n_best=True)
                sentences = []
                for sent in n_best:
                    sentences.append(sent.split("|||")[1])
                del translator  # Free GPU slot

                inspect_details = {
                    "source": engine.source.code,
                    "target": engine.target.code,
                    "preproc_input": line_tok,
                    "preproc_output": tokenizer.tokenize(sentences[0]),
                    "nbest": sentences,
                    "alignments": [],
                    "postproc_output": sentences[0],
                }

    return inspect_details


@celery.task(bind=True)
def inspect_compare(self, user_id, line, engines):
    translations = []
    with app.app_context():
        for engine_id in engines:
            engine = Engine.query.filter_by(id=engine_id).first()
            translations.append(
                {
                    "id": engine_id,
                    "name": engine.name,
                    "text": translate_text(user_id, engine_id, [line]),
                }
            )

        return {
            "source": engine.source.code,
            "target": engine.target.code,
            "translations": translations,
        }


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# EVALUATE TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@celery.task(bind=True)
def evaluate_files(self, user_id, mt_paths, ht_paths, source_path=None):
    # Transform utf-8 with BOM (if it is) to utf-8
    for path in mt_paths + ht_paths + [source_path]:
        if path:
            data_utils.convert_file_to_utf8(path)
            data_utils.fix_file(path)

    # Load evaluators from ./evaluators folder
    evaluators: Evaluator = []
    for minfo in pkgutil.iter_modules([app.config["EVALUATORS_FOLDER"]]):
        module = importlib.import_module(
            ".{}".format(minfo.name), package="app.blueprints.evaluate.evaluators"
        )
        classes = inspect.getmembers(module)
        for name, _class in classes:
            if (
                name != "Evaluator"
                and name.lower() == minfo.name.lower()
                and inspect.isclass(_class)
            ):
                evaluator = getattr(module, name)
                evaluators.append(evaluator())

    lexical_var = ttr.Ttr()
    all_evals = []
    for mt_path in mt_paths:
        evals = []

        for ht_path in ht_paths:
            ht_eval = []
            for evaluator in evaluators:
                try:
                    ht_eval.append(
                        {
                            "name": evaluator.get_name(),
                            "value": evaluator.get_value(mt_path, ht_path, source_path),
                            "is_metric": True,
                        }
                    )
                except:
                    # If a metric throws an error because of things,
                    # we just skip it for now
                    pass

            ## Lexical variety for original, MT translation and reference
            for path in [mt_path, ht_path]:
                if path:
                    ht_eval.append(
                        {
                            "name": "{}".format(
                                "MT"
                                if path == mt_path
                                else "REF" if path == ht_path else ""
                            ),
                            "value": lexical_var.compute(path),
                            "is_metric": False,
                        }
                    )

            evals.append(ht_eval)

        all_evals.append(evals)

    xlsx_file_paths = []
    ht_rows = []
    for ht_index, ht_path in enumerate(ht_paths):
        rows = []
        with open(ht_path, "r") as ht_file:
            for i, line in enumerate(ht_file):
                line = line.strip()
                rows.append(
                    ["Ref {}".format(ht_index + 1), line, None, None, i + 1, []]
                )

        for mt_path in mt_paths:
            scores = spl(mt_path, ht_path, source_path)
            for i, score in enumerate(scores):
                rows[i][5].append(score)

        if source_path:
            with open(source_path, "r") as source_file:
                for i, line in enumerate(source_file):
                    rows[i].append(line.strip())

        xlsx_file_paths.append(generate_xlsx(user_id, rows, ht_index))

        ht_rows.append(rows)

    for path in mt_paths + ht_paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            # It was the same file, we just pass
            pass

    return {"result": 200, "evals": all_evals, "spl": ht_rows}, xlsx_file_paths


def spl(mt_path, ht_path, source_path):
    # Scores per line (bleu, comet, chrf3 and ter)
    logger.info([mt_path, ht_path])
    rows = []

    # Obtain Bleu results in output file
    sacreBLEU = subprocess.Popen(
        "cat {} | sacrebleu -sl -b {} > {}.bpl".format(mt_path, ht_path, mt_path),
        cwd=app.config["TMP_FOLDER"],
        shell=True,
        stdout=subprocess.PIPE,
    )
    sacreBLEU.wait()

    # Obtain CHRF3 results in output file
    sacreCHRF = subprocess.Popen(
        "cat {} | sacrebleu -sl -b {} -m chrf --chrf-beta 3 > {}.chrfpl".format(
            mt_path, ht_path, mt_path
        ),
        cwd=app.config["TMP_FOLDER"],
        shell=True,
        stdout=subprocess.PIPE,
    )
    sacreCHRF.wait()

    # Obtain Comet results in output file
    if source_path != "":
        src_path = "-s {0}".format(source_path)

    with app.app_context():
        # for commet calculation, check first if there is an available GPU
        # if not, then use CPU to calculate it, though it will take a lot longer
        gpu_id = GPUManager.get_available_device()
        if gpu_id is not None:
            device_command = f"-d {gpu_id}"

            comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} -o {3}.cpl {4} --workspace 4000 --mini-batch 1".format(mt_path, src_path, ht_path, mt_path, device_command),
                                    shell=True, stdout=subprocess.PIPE)

            GPUManager.free_device(gpu_id)
            db.session.commit()
        else:
            comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} -o {3}.cpl -c 8".format(mt_path, src_path, ht_path, mt_path),
                                    shell=True, stdout=subprocess.PIPE)

    # Bleu rows
    with open("{}.bpl".format(mt_path), "r") as bl_file:
        rows = [{"bleu": line.strip()} for line in bl_file]
    os.remove("{}.bpl".format(mt_path))

    # Comet and CHRF3 rows
    with open("{}.cpl".format(mt_path), "r") as cl_file, open(
        "{}.chrfpl".format(mt_path), "r"
    ) as chrfl_file:
        for i, row in enumerate(rows):
            score_cl = cl_file.readline().strip()
            score_chrfl = chrfl_file.readline().strip()
            rows[i]["comet"] = score_cl
            rows[i]["chrf3"] = score_chrfl
    os.remove("{}.cpl".format(mt_path))
    os.remove("{}.chrfpl".format(mt_path))

    # TER rows
    with open(ht_path) as ht_file, open(mt_path) as mt_file:
        for i, row in enumerate(rows):
            ht_line = ht_file.readline().strip()
            mt_line = mt_file.readline().strip()
            if ht_line and mt_line:
                ter = round(pyter.ter(ht_line.split(), mt_line.split()), 2)
                rows[i]["ter"] = 100 if ter > 1 else utils.parse_number(ter * 100, 2)
                rows[i]["text"] = mt_line

    return rows


def generate_xlsx(user_id, rows, ht_path_index):
    file_name = utils.normname(user_id, "evaluation") + ".xlsx"
    file_path = utils.tmpfile(file_name)

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    x_rows = []
    for i, row in enumerate(rows):
        x_row = [i + 1]

        if len(row) > 6:
            x_row = [i + 1, row[6]]

        for mt_data in row[5]:
            x_row.append(mt_data["text"])

        x_row.append(row[1])

        for mt_data in row[5]:
            x_row.append(mt_data["bleu"])

        for mt_data in row[5]:
            x_row.append(mt_data["ter"])

        x_rows.append(x_row)

    headers = ["Line"]
    headers = headers + (["Source sentence"] if len(row) > 6 else [])
    headers = headers + [
        "Machine translation {}".format(i + 1) for i in range(len(row[5]))
    ]
    headers = headers + ["Reference {}".format(ht_path_index + 1)]

    headers = headers + ["Bleu MT{}".format(i + 1) for i in range(len(row[5]))]
    headers = headers + ["TER MT{}".format(i + 1) for i in range(len(row[5]))]

    x_rows = [headers] + x_rows

    row_cursor = 0
    for row in x_rows:
        for col_cursor, col in enumerate(row):
            worksheet.write(row_cursor, col_cursor, col)
        row_cursor += 1

    workbook.close()

    return file_path


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# UPLOAD TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@celery.task(bind=True)
def process_upload_request(
    self,
    user_id,
    bitext_path,
    src_path,
    trg_path,
    src_lang,
    trg_lang,
    corpus_name,
    corpus_desc="",
    corpus_topic=None,
    opus = False
):
    type = "bitext" if bitext_path else "bilingual" if trg_path else "monolingual"

    def process_file(file, language, corpus, role):
        with app.app_context():
            db_file = data_utils.upload_file(file, language, user_id=user_id)

            if role == "source":
                corpus.user_source_id = language
            else:
                corpus.user_target_id = language

            db.session.add(db_file)
            db.session.commit()
            corpus.corpus_files.append(Corpus_File(db_file, role=role))

        return db_file

    def process_bitext(file):
        file_name, file_extension = os.path.splitext(file.filename)
        norm_name = utils.normname(user_id=user_id, filename=file_name)
        tmp_file_fd, tmp_path = utils.tmpfile()
        file.save(tmp_path)

        data_utils.convert_file_to_utf8(tmp_path)
        data_utils.fix_file(tmp_path)

        if file_extension == ".tmx":
            with open(
                utils.filepath("FILES_FOLDER", norm_name + "-src"), "w"
            ) as src_file, open(
                utils.filepath("FILES_FOLDER", norm_name + "-trg"), "w"
            ) as trg_file, open(
                tmp_path, "rb"
            ) as tmx_file:
                inside_tuv = False
                seg_text = []
                tu = []

                def se(name, _):
                    nonlocal inside_tuv
                    if name == "seg":
                        inside_tuv = True

                def lp(line):
                    return re.sub(r"[\r\n\t\f\v]", " ", line.strip())

                def ee(name):
                    nonlocal inside_tuv, seg_text, tu, src_file
                    if name == "seg":
                        inside_tuv = False
                        tu.append("".join(seg_text))
                        seg_text = []

                        if len(tu) == 2:
                            print(lp(tu[0]), file=src_file)
                            print(lp(tu[1]), file=trg_file)
                            tu = []

                def cd(data):
                    nonlocal inside_tuv, seg_text
                    if inside_tuv:
                        seg_text.append(data)

                parser = xml.parsers.expat.ParserCreate()
                parser.StartElementHandler = se
                parser.EndElementHandler = ee
                parser.CharacterDataHandler = cd
                parser.ParseFile(tmx_file)

        else:
            # We assume it is a TSV
            with open(
                utils.filepath("FILES_FOLDER", norm_name + "-src"), "wb"
            ) as src_file, open(
                utils.filepath("FILES_FOLDER", norm_name + "-trg"), "wb"
            ) as trg_file, open(
                tmp_path, "r"
            ) as tmp_file:
                for line in tmp_file:
                    cols = line.strip().split("\t")
                    src_file.write((cols[0] + "\n").encode("utf-8"))
                    trg_file.write((cols[1] + "\n").encode("utf-8"))

        src_file = open(utils.filepath("FILES_FOLDER", norm_name + "-src"), "rb")
        trg_file = open(utils.filepath("FILES_FOLDER", norm_name + "-trg"), "rb")

        return FileStorage(src_file, filename=file.filename + "-src"), FileStorage(
            trg_file, filename=file.filename + "-trg"
        )

    with app.app_context():
        # We create the corpus, retrieve the files and attach them to that corpus
        target_db_file = None
        try:
            
            public = False
            visible = True
            opus_corpus = False
            if opus:
                public = True
                opus_corpus = True
            
            corpus = Corpus(
                name=corpus_name,
                type="bilingual" if type == "bitext" else type,
                owner_id=user_id,
                description=corpus_desc,
                topic_id=corpus_topic,
                public=public,
                visible=visible,
                opus_corpus=opus_corpus
            )

            if type == "bitext":
                with open(bitext_path, "rb") as fbitext:
                    bitext_file = FileStorage(
                        fbitext, filename=os.path.basename(fbitext.name)
                    )
                    src_file, trg_file = process_bitext(bitext_file)

                    source_db_file = process_file(src_file, src_lang, corpus, "source")
                    target_db_file = process_file(trg_file, trg_lang, corpus, "target")

            else:
                with open(src_path, "rb") as fsrctext:
                    src_file = FileStorage(
                        fsrctext, filename=os.path.basename(fsrctext.name)
                    )
                    source_db_file = process_file(src_file, src_lang, corpus, "source")

                if type == "bilingual":
                    with open(trg_path, "rb") as ftrgtext:
                        trg_file = FileStorage(
                            ftrgtext, filename=os.path.basename(ftrgtext.name)
                        )
                        target_db_file = process_file(
                            trg_file, trg_lang, corpus, "target"
                        )
                    
                    if opus:
                        os.remove(src_path)
                        os.remove(trg_path)

            db.session.add(corpus)
            db.session.commit()

            user = User.query.filter_by(id=user_id).first()
            user.user_corpora.append(LibraryCorpora(corpus=corpus, user=user))
        except Exception as e:
            db.session.rollback()
            db.session.remove()
            raise Exception("Something went wrong on our end... Please, try again later")

        if target_db_file:
            source_lines = utils.file_length(source_db_file.path)
            target_lines = utils.file_length(target_db_file.path)

            if source_lines != target_lines:
                db.session.rollback()
                db.session.remove()
                raise Exception("Source and target file should have the same length")

        db.session.commit()
        db.session.remove()

    return True

@celery.task(bind=True)
def download_opus_dataset(self, path_to_script, url_to_download, 
                            opus_workdir, src_lang, trg_lang, corpus_name, TEMP_LOG_FILE, USER_ID, 
                            source_file, target_file, source_lang_id, target_lang_id, corpus_dir):
        
    subprocess.run("bash {0} {1} {2} {3} {4} {5} {6} {7}".format(path_to_script, url_to_download, opus_workdir, src_lang, trg_lang, corpus_name, TEMP_LOG_FILE, corpus_dir), shell=True, stdout=subprocess.PIPE)

    # Call data_utils.process_upload_request or something similar and simulate all the needed parameters
    # however, instantly set the corpus as public and as visible
    task_id = data_utils.process_upload_request(USER_ID, 
                                                None,
                                                source_file,
                                                target_file,
                                                source_lang_id,
                                                target_lang_id,
                                                corpus_name,
                                                f"{corpus_name} dataset, downloaded from the OPUS collection",
                                                "General",
                                                opus = True,
                                                asynchr = False)

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Pre- post- tasks to allocate GPUs for translation
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


@task_prerun.connect
def reserve_gpu(sender=None, **kwargs):
    name = sender.name.split(".")[-1]
    is_admin = sender.request.args[-1]
    if name in (
        "translate_text",
        "translate_file",
        "inspect_details",
        "inspect_compare",
    ):
        device = GPUManager.wait_for_available_device(is_admin=is_admin)
        if device is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = str(device)
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
        logging.debug(f"Task {sender.name}[{sender.request.id}] reserved GPU {device}")


@task_postrun.connect
def free_gpu(sender=None, **kwargs):
    name = sender.name.split(".")[-1]
    if name in (
        "translate_text",
        "translate_file",
        "inspect_details",
        "inspect_compare",
    ):
        if os.environ["CUDA_VISIBLE_DEVICES"]:
            device = os.environ["CUDA_VISIBLE_DEVICES"]
            GPUManager.free_device(int(device))
            logging.debug(f"Task {sender.name}[{sender.request.id}] freed GPU {device}")
