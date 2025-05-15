from app import app, db
from app.flash import Flash
from app.models import LibraryCorpora, LibraryEngine, Engine, File, Corpus_Engine, Corpus, User, Corpus_File, Language, \
    UserLanguage
from app.utils import user_utils, utils, data_utils, tensor_utils, tasks, finetuning_log
from app.utils.roles import EnumRoles
from app.utils.finetuner import Finetuner
from app.utils.power import PowerUtils
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import func
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import namegenerator
import datetime
from werkzeug.datastructures import FileStorage
from celery.result import AsyncResult
from functools import reduce

import traceback
import hashlib
import os
import yaml
import shutil
import sys
import ntpath
import subprocess
import glob
import re
import json
import logging

finetune_blueprint = Blueprint('finetune', __name__, template_folder='templates')

@finetune_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_index():
    currently_finetuning = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("finetuning")).all()

    if (len(currently_finetuning) > 0):
        return redirect(url_for('finetune.finetune_console', id=currently_finetuning[0].id))

    currently_launching = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("launching")).all()
                            
    if (len(currently_launching) > 0): 
        return redirect(url_for('finetune.finetune_launching', task_id=currently_launching[0].bg_task_id))

    random_name = namegenerator.gen()
    tryout = 0
    while len(Engine.query.filter_by(name = random_name).all()):
        random_name = namegenerator.gen()
        tryout += 1

        if tryout >= 5:
            random_name = ""
            break

    random_name = " ".join(random_name.split("-")[:2])

    library_corpora = user_utils.get_user_corpora().filter(LibraryCorpora.corpus.has(Corpus.type == "bilingual")).all()
    corpora = [c.corpus for c in library_corpora]
    languages = UserLanguage.query.filter_by(user_id=current_user.id).order_by(UserLanguage.name).all()

    return render_template('finetune.html.jinja2', page_name='finetune', page_title='Finetune',
                            corpora=corpora, random_name=random_name,
                            languages=languages)

@finetune_blueprint.route('/launching/<task_id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_launching(task_id):
    if user_utils.is_normal(): return redirect(url_for('index'))

    return render_template('launching.html.jinja2', page_name='finetune', page_title='Launching finetuning', task_id=task_id)

@finetune_blueprint.route('/start', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_start():
    if user_utils.is_normal(): return url_for('index')
    engine_path = os.path.join(user_utils.get_user_folder("engines"), utils.normname(user_utils.get_user().username, request.form['nameText']))
    task = tasks.launch_finetuning.apply_async(args=[user_utils.get_uid(), engine_path, { i[0]: i[1] if i[0].endswith('[]') else i[1][0] for i in request.form.lists()}])

    return jsonify({ "result": 200, "launching_url": url_for('finetune.finetune_launching', task_id=task.id) })

@finetune_blueprint.route('/launch_status', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def launch_status():
    task_id = request.form.get('task_id')
    result = tasks.launch_finetuning.AsyncResult(task_id)

    if result and result.status == "SUCCESS":
        engine_id = result.get()
        if engine_id != -1:
            return jsonify({ "result": 200, "engine_id": result.get() })
        else:
            return jsonify({ "result": -2 })
    else:
        return jsonify({ "result": -1 })
    
import pytz    

@finetune_blueprint.route('/launch', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_launch():
    id = request.form.get('engine_id')
    if user_utils.is_normal(): return url_for('index')

    task_id, monitor_task_id = finetuner.launch(id, user_utils.get_user_role())

    return url_for('finetune.finetune_console', id=id)

@finetune_blueprint.route('/console/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_console(id):    
    engine = Engine.query.filter_by(id = id).first()
    config_file_path = os.path.join(os.path.realpath(os.path.join(app.config['PRELOADED_ENGINES_FOLDER'], engine.path)), 'config.yaml')
    config = None

    try:
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
    except:
        pass

    launched = engine.launched.astimezone(pytz.UTC).timestamp()
    finished = datetime.datetime.timestamp(engine.finished) if engine.finished else None

    corpora_raw = Corpus_Engine.query.filter_by(engine_id = engine.id, is_info = True).all()

    corpora = {}
    for corpus_entry in corpora_raw:
        if corpus_entry.phase in corpora:
            corpora[corpus_entry.phase].append((corpus_entry.corpus, utils.format_number(corpus_entry.selected_size, abbr=True)))
        else:
            corpora[corpus_entry.phase] = [(corpus_entry.corpus, utils.format_number(corpus_entry.selected_size, abbr=True))]

    return render_template("finetune_console.html.jinja2", page_name="finetune",
            engine=engine, config=config,
            launched = launched, finished = finished,
            elapsed = engine.runtime, corpora=corpora, elapsed_format=utils.seconds_to_timestring(engine.runtime) if engine.runtime else None)

@finetune_blueprint.route('/full_finetuning_graph', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def full_finetune_graph():
    id = request.form.get('engine_id')

    try:
        engine = Engine.query.filter_by(id=id).first()
        
        graph_dict_path = os.path.join(engine_path, "full_graph.yaml")

        stats = {}

        stats_aux = {}
        with open(graph_dict_path) as f:
            stats_aux = yaml.safe_load(f)

        for tag in stats_aux.keys():
            if tag != "finetune/finetune_epoch":
                stats[tag] = []
                data_len = len(stats_aux[tag])

                data_breakpoint = 1000 if data_len >= 100 else 10 if data_len > 10 else 1

                for i, item in enumerate(stats_aux[tag]):
                        if item["step"] % data_breakpoint == 0 or (i + 1) == data_len:
                            stats[tag].append({"time": item["time"], "step": item["step"], "value": item["value"]})
                if tag == "finetune/finetune_learning_rate":
                    stats[tag] = stats[tag][1:]

    except Exception as ex:
        logging.exception("An exception was thrown in FULL_FINETUNE_GRAPH")

    return jsonify({"stats": stats })

@finetune_blueprint.route('/historic_finetuning_data', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def historic_finetune_graph():
    id = request.form.get('engine_id')
    graph_id = request.form.get('graph_id')

    try:
        engine = Engine.query.filter_by(id=id).first()
        
        graph_log = os.path.join(engine.path, "graph_logs.yaml")

        with open(graph_log, "r") as f:
            graphs_dict = yaml.load(f, Loader = yaml.FullLoader)
        graph_dict_path = graphs_dict[int(graph_id)]

        stats = {}

        stats_aux = {}
        with open(graph_dict_path) as f:
            stats_aux = yaml.safe_load(f)

        for tag in stats_aux.keys():
            if tag != "finetune/finetune_epoch":
                stats[tag] = []
                data_len = len(stats_aux[tag])

                data_breakpoint = 1000 if data_len >= 100 else 10 if data_len > 10 else 1

                for i, item in enumerate(stats_aux[tag]):
                        if item["step"] % data_breakpoint == 0 or (i + 1) == data_len:
                            stats[tag].append({"time": item["time"], "step": item["step"], "value": item["value"]})
                if tag == "finetune/finetune_learning_rate":
                    stats[tag] = stats[tag][1:]

    except Exception as ex:
        logging.exception("An exception was thrown in HISTORIC_finetune_GRAPH")

    return jsonify({"stats": stats })

@finetune_blueprint.route('/graph_data', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_graph():
    tags = request.form.getlist('tags[]')
    id = request.form.get('id')

    try:
        engine = Engine.query.filter_by(id=id).first()

        if engine.model_path:
            graph_dict_path = os.path.join(engine.model_path, 'graph_dict.yaml')
        else:
            graph_dict_path = os.path.join(engine.path, 'model/graph_dict.yaml')

        stats = {}

        stats_aux = {}
        with open(graph_dict_path) as f:
            stats_aux = yaml.safe_load(f)

        for tag in stats_aux.keys():
            if tag != "finetune/finetune_epoch":
                stats[tag] = []
                data_len = len(stats_aux[tag])

                data_breakpoint = 1000 if data_len >= 100 else 10 if data_len > 10 else 1

                for i, item in enumerate(stats_aux[tag]):
                        if item["step"] % data_breakpoint == 0 or (i + 1) == data_len:
                            stats[tag].append({"time": item["time"], "step": item["step"], "value": item["value"]})
                if tag == "finetune/finetune_learning_rate":
                    stats[tag] = stats[tag][1:]

    except Exception as ex:
        logging.exception("An exception was thrown in finetune_GRAPH")

    return jsonify({ "stopped": engine.has_stopped(), "stats": stats })

@finetune_blueprint.route('/finetune_status', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_status():
    id = request.form.get('id')

    engine = Engine.query.filter_by(id = id).first()
    tensor = tensor_utils.TensorUtils(id)

    graph_dict_path = os.path.join(engine.model_path, 'graph_dict.yaml')
    stats_aux = {}
    stats = {}
    if os.path.isfile(graph_dict_path):
        with open(graph_dict_path) as f:
            stats_aux = yaml.safe_load(f)
    
    if stats_aux != {} and "finetune/finetune_epoch" in stats_aux and stats_aux["finetune/finetune_epoch"] != []:
        epoch_no = 0
        for epoch in stats_aux["finetune/finetune_epoch"]:
            if int(epoch) > epoch_no:
                epoch_no = epoch
        stats["epoch"] = epoch_no

        launched = engine.launched
        finished = engine.finished if engine.finished else None
        now = datetime.datetime.utcnow().replace(tzinfo=None)
        elapsed = (now - launched).total_seconds() if not engine.has_stopped() else (finished - launched).total_seconds()
        power = engine.power if engine.power else 0
        power_reference = PowerUtils.get_reference_text(power, elapsed)
        power_wh = power * (elapsed / 3600)

        return jsonify({ "stopped": engine.has_stopped(), "stats": stats, "done": engine.bg_task_id is None,
                            "power": int(power_wh), "power_reference": power_reference, 
                            "test_task_id": engine.test_task_id, "test_score": engine.test_score })
    else:
        return jsonify({ "stats": [], "stopped": engine.has_stopped() })

@finetune_blueprint.route('/finetune_stats', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_stats():
    engine_id = request.form.get('id')
    engine = Engine.query.filter_by(id=engine_id).first()

    score = 0.0
    ppl = "—"
    tps = []
    
    try:
        graph_dict = {}
        graph_dict["finetune/finetune_batch_loss"] = []
        graph_dict["finetune/finetune_learning_rate"] = []
        graph_dict["valid/valid_ppl"] = []
        graph_dict["valid/valid_score"] = []
        graph_dict["finetune/finetune_epoch"] = []

        with open(os.path.join(engine.model_path, "finetune.log"), 'r') as log_file:
            for line in log_file:
                groups = re.search(finetuning_log.finetuning_regex, line, flags=finetuning_log.re_flags)
                if groups:
                    tps.append(float(groups.groups()[8]))
                    time_g = groups.groups()[1]
                    step_g = int(groups.groups()[4])
                    graph_dict["finetune/finetune_batch_loss"].append({"time": time_g, "step": step_g, "value": float(groups.groups()[6])})
                    graph_dict["finetune/finetune_learning_rate"].append({"time": time_g, "step": step_g, "value": float(groups.groups()[10])})
                    graph_dict["finetune/finetune_epoch"].append(int(groups.groups()[3]))
                else:
                    # It was not a finetuning line, could be validation
                    groups = re.search(finetuning_log.validation_regex, line, flags=finetuning_log.re_flags)
                    if groups:
                        time_g = groups.groups()[1]
                        step_g = int(groups.groups()[4])
                        if groups.groups()[5] == "bleu":
                            bleu_score = float(groups.groups()[6])
                            score = bleu_score if bleu_score > score else score
                            graph_dict["valid/valid_score"].append({"time": time_g, "step": step_g, "value": score})
                        
                        if groups.groups()[5] == "perplexity":
                            ppl = float(groups.groups()[6])
                            graph_dict["valid/valid_ppl"].append({"time": time_g, "step": step_g, "value": ppl})

        graph_dict_path = os.path.join(engine.model_path, 'graph_dict.yaml')
        with open(graph_dict_path, 'w+') as outfile:
            yaml.dump(graph_dict, outfile, default_flow_style=False)

    except Exception as ex:
        logging.exception("An exception was thrown in finetune_STATS")

    if len(tps) > 0:
        tps_value = reduce(lambda a, b: a + b, tps)
        tps_value = round(tps_value / len(tps))
    else:
        tps_value = "—"
    
    time_elapsed = None
    if engine.runtime:
        time_elapsed = engine.runtime

        if time_elapsed:
            time_elapsed_format = utils.seconds_to_timestring(time_elapsed)
        else:
            time_elapsed_format = "—"
    else:
        time_elapsed_format = "—"

    data = {
        "time_elapsed": time_elapsed_format,
        "tps": tps_value,
        "score": score,
        "ppl": ppl,
    }

    config_file_path = os.path.join(engine.path, 'config.yaml')
    with open(config_file_path, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)

        data["val_freq"] = config["valid-freq"] if "valid-freq" in config else None
        data["patience"] = config["early-stopping"] if "early-stopping" in config else None 
        data["beam_size"] = config["beam-size"] if "beam-size" in config else None

        # get epochs parameter from "after" and convert to int
        epoch_number = int(re.findall(r'\d+', config["after"])[0])
        data["epochs"] = epoch_number if "after" in config else None

        data["batch_size"] = config["mini-batch"] if "mini-batch" in config else None 

    data["vocab_size"] = config["dim-vocabs"][0] if "dim-vocabs" in config else None

    return jsonify({
        "result": 200, 
        "data": data
    })

    

@finetune_blueprint.route('/log', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_log():
    engine_id = request.form.get('engine_id')
    draw = request.form.get('draw')
    search = request.form.get('search[value]')
    start = int(request.form.get('start'))
    length = int(request.form.get('length'))
    order = int(request.form.get('order[0][column]'))
    dir = request.form.get('order[0][dir]')

    engine = Engine.query.filter_by(id = engine_id).first()
    if engine.model_path:
        finetune_log_path = os.path.join(engine.model_path, 'finetune.log')
    else:
        finetune_log_path = os.path.join(engine.path, 'model/finetune.log')

    rows = []
    try:
        with open(finetune_log_path, 'r') as finetune_log:
            re_flags = re.IGNORECASE | re.UNICODE
            for line in finetune_log:
                groups = re.search(finetuning_log.finetuning_regex, line.strip(), flags=re_flags)
                if groups:
                    date_string = groups.groups()[0]
                    time_string = groups.groups()[1]
                    epoch, step = int(groups.groups()[3]), int(groups.groups()[4])
                    batch_loss, tps, lr = float(groups.groups()[6]), float(groups.groups()[8]), float(groups.groups()[10])

                    # date = datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
                    rows.append([time_string, epoch, step, batch_loss, tps, lr])
    except Exception as ex:
        logging.exception("An exception was thrown in finetune_LOG")

    if order is not None:
        rows.sort(key=lambda row: row[order], reverse=(dir == "desc"))

    final_rows = rows

    if start is not None and length is not None:
        final_rows = rows[start:(start + length)]

    rows_filtered = []
    if search:
        for row in final_rows:
            found = False

            for col in row:
                if not found:
                    if search in col:
                        rows_filtered.append(row)
                        found = True

    return jsonify({
        "draw": int(draw) + 1,
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows_filtered) if search else len(rows),
        "data": rows_filtered if search else final_rows
    })


@finetune_blueprint.route('/attention/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_attention(id):
    if user_utils.is_normal(): return send_file(os.path.join(app.config['BASE_CONFIG_FOLDER'], "attention.png"))

    engine = Engine.query.filter_by(id = id).first()
    files = glob.glob(os.path.join(engine.path, "*.att"))
    if len(files) > 0:
        return send_file(files[0])
    else:
        return send_file(os.path.join(app.config['BASE_CONFIG_FOLDER'], "attention.png"))


def _finetune_stop(id, user_stop):
    finetuner.stop(id, user_stop=user_stop)
    return redirect(url_for('finetune.finetune_console', id=id))

@finetune_blueprint.route('/stop/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_stop(id):
    if user_utils.is_normal(): return redirect(url_for('index'))
        
    return _finetune_stop(id, True)

@finetune_blueprint.route('/finish/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_finish(id):
    if user_utils.is_normal(): return redirect(url_for('index'))
        
    return _finetune_stop(id, False)

@finetune_blueprint.route('/resume/<engine_id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_resume(engine_id):
    try:
        if user_utils.is_normal(): return redirect(url_for('index'))

        engine = Engine.query.filter_by(id=engine_id).first()

        if current_user.id == engine.engine_users[0].user.id or user_utils.is_admin():
            # create new separate path for the next model with some random id in the path
            new_model_path = os.path.join(engine.path, 'model-{}'.format(utils.randomfilename(length=8)))
            while os.path.exists(new_model_path):
                # if random path already exists, try it again until it doesn't
                new_model_path = os.path.join(engine.path, 'model-{}'.format(utils.randomfilename(length=8)))
            
            os.makedirs(new_model_path)

            # create file to actual model npz file
            model_file_path = os.path.join(new_model_path, "model")

            # load configuration yaml file and change the model's path with the new one
            config_file_path = os.path.join(engine.path, 'config.yaml')
            config = None
            with open(config_file_path, 'r') as config_file:
                config = yaml.load(config_file, Loader=yaml.FullLoader)
                current_model = config["model"]
                config["model"] = os.path.join(new_model_path, "model.npz")
                config["log"] = os.path.join(new_model_path, "finetune.log")

            with open(config_file_path, 'w') as config_file:
                yaml.dump(config, config_file)

            # update the model with the new information
            engine.model_path = new_model_path
            engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)
            engine.finished = None
            db.session.commit()

            task_id, _ = finetuner.launch(engine_id, user_utils.get_user_role(), refinetune_path = current_model)
            i = 0
            while engine.has_stopped() and i < 100:
                db.session.refresh(engine)
                i += 1

            return redirect(url_for('finetune.finetune_console', id=engine_id))
    except Exception as ex:
        print(str(ex), flush = True)
        return -1

@finetune_blueprint.route('/test', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_test():
    if user_utils.is_normal(): return redirect(url_for('index'))

    engine_id = request.form.get('engine_id')
    task = tasks.test_finetuning.apply_async(args=[engine_id])

    engine = Engine.query.filter_by(id=engine_id).first()
    engine.test_task_id = task.id
    db.session.commit()

    return task.id

@finetune_blueprint.route('/test_status', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_test_status():
    if user_utils.is_normal(): return redirect(url_for('index'))

    task_id = request.form.get('task_id')
    task_success, task_value = utils.get_task_result(tasks.test_finetuning, task_id)
    if task_success is not None:
        if not task_success:
            return jsonify({ "result": -2 })
        return jsonify({ "result": 200, "test": task_value })
    else:
        return jsonify({ "result": -1 })

@finetune_blueprint.route('/get-opus-models', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def get_opus_models():
    model_list = []

    try:
        USER_ID = user_utils.get_uid()

        src_lang = request.form.get("source_lang")
        trg_lang = request.form.get("target_lang")

        source_lang_db = UserLanguage.query.filter_by(code=src_lang, user_id=USER_ID).first()
        target_lang_db = UserLanguage.query.filter_by(code=trg_lang, user_id=USER_ID).first()

        if source_lang_db and target_lang_db:
            model_list_query = Engine.query.filter_by(user_source_id=source_lang_db.id, 
                                            user_target_id=target_lang_db.id,
                                            opus_engine=True).all()
            
            for model_obj in model_list_query:
                model_dict = {}
                model_dict["id"] = model_obj.id
                model_dict["name"] = model_obj.name
                model_list.append(model_dict)

    except Exception as e:
        return jsonify({"result": -1, "info": str(e)})

    return jsonify({"result": 200, "model_list": model_list})
