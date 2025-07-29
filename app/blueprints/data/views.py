from app import app, db
from app.models import File, Corpus, Corpus_File, LibraryCorpora, User, UserLanguage
from app.utils import utils, user_utils, data_utils, tasks
from app.flash import Flash
from flask import Blueprint, render_template, request, jsonify, flash, url_for, redirect
from flask_login import login_required, current_user
from sqlalchemy import desc, select, exists
from celery.result import AsyncResult

import os
import requests
import subprocess
import hashlib
import re
import datetime
import shutil
import sys

data_blueprint = Blueprint('data', __name__, template_folder='templates')

@data_blueprint.route('/preview/<file_id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_preview(file_id):
    file = File.query.filter_by(id=file_id).first()
    lines = []
    with open(file.path, 'r') as reader:
        for i, line in enumerate(reader):
            if i < 50:
                lines.append(line)
            else:
                break

    return render_template('preview.data.html.jinja2', page_name='library_corpora_file_preview', file=file, lines=lines)

@data_blueprint.route('/upload', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload_perform():
    if user_utils.is_normal(): return redirect(url_for('index'))

    try:
        if request.method == 'POST':

            source_lang = request.form.get('source_lang')
            target_lang = request.form.get('target_lang')

            custom_src_lang_code = request.form.get('sourceCustomLangCode')
            custom_trg_lang_code = request.form.get('targetCustomLangCode')

            if custom_src_lang_code:
                custom_src_lang_name = request.form.get('sourceCustomLangName')
                custom_lang = user_utils.add_custom_language(custom_src_lang_code, custom_src_lang_name)

                source_lang = custom_lang.id
            else:
                source_lang = UserLanguage.query.filter_by(code=source_lang, user_id=current_user.id).one().id

            if custom_trg_lang_code:
                custom_trg_lang_name = request.form.get('targetCustomLangName')
                custom_lang = user_utils.add_custom_language(custom_trg_lang_code, custom_trg_lang_name)

                target_lang = custom_lang.id
            else:
                target_lang = UserLanguage.query.filter_by(code=target_lang, user_id=current_user.id).one().id
            
            task_id = data_utils.process_upload_request(user_utils.get_uid(), request.files.get('bitext_file'), request.files.get('source_file'),
                    request.files.get('target_file'), source_lang, target_lang,
                    request.form.get('name'), request.form.get('description'), request.form.get('topic'))

            return jsonify({ "result": 200, "task_id": task_id })
        else:
            raise Exception("Sorry, but we couldn't handle your request.")
    except Exception as e:
        Flash.issue(e, Flash.ERROR)

    return jsonify({ "result": -1 })

@data_blueprint.route('/upload_status', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload_status():
    task_id = request.form.get('task_id')
    task_success, task_value = utils.get_task_result(tasks.process_upload_request, task_id)
    if task_success is not None:
        if not task_success:
            exception_text = task_value if type(task_value) is Exception else None
            Flash.issue("Something went wrong" if exception_text is None else "Something went wrong: {}".format(exception_text), Flash.ERROR)
            return jsonify({ "result": -2 })

        Flash.issue("Corpus successfully uploaded and added to <a href='#your_corpora'>your corpora</a>.",
                    Flash.SUCCESS, markup=True)
        return jsonify({ "result": 200 })
    else:
        return jsonify({ "result": -1 })

@data_blueprint.route('/get-opus-corpora', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def get_opus_corpora_by_langs():
    src_lang = request.form.get('source_lang')
    trg_lang = request.form.get('target_lang')

    src_lang_code_custom = request.form.get('source_lang_code_custom')
    trg_lang_code_custom = request.form.get('target_lang_code_custom')

    # if either source or target custom language boxes have value,
    # set the real source/target with said value to search in OPUS
    if src_lang_code_custom:
            src_lang = src_lang_code_custom

    if trg_lang_code_custom:
            trg_lang = trg_lang_code_custom

    full_url = f"http://opus.nlpl.eu/opusapi/?&source={src_lang}&target={trg_lang}&preprocessing=moses&version=latest"
    data = requests.get(full_url)

    output = data.json()
    datasets = []

    src_lang_aux = src_lang
    if src_lang > trg_lang:
        src_lang = trg_lang 
        trg_lang = src_lang_aux

    for line in output["corpora"]:
        if line["source"] == src_lang and line["target"] == trg_lang:
            datasets.append(line)
    db.session.remove()

    return jsonify({ "result": 200, "datasets": datasets })

@data_blueprint.route('/check-opus-corpus', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def check_opus_corpus():
    try:
        src_lang = request.form.get('source_lang')
        trg_lang = request.form.get('target_lang')
        corpus_name = request.form.get('corpus_name')

       # to check if an OPUS corpus has already been downloaded by anyone
        # we have to use all the corpora with the given name and then 
        # check if the input src and trg languages are the same as
        # any of the corpora that are obtained by the query
        all_corpora = Corpus.query.filter_by(name=corpus_name).all()

        for corpus in all_corpora:
            if src_lang == corpus.source.code and trg_lang == corpus.target.code:
                db.session.remove()
                return jsonify({ "result": -1 }) 
        
        db.session.remove()

        return jsonify({ "result": 200})
    except Exception as ex:
        print("Exception in check_opus_corpus: " + str(ex), flush = True)
        return jsonify({ "result": -2})

@data_blueprint.route('/download-opus-corpus', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def download_opus_corpus():
    try:
        src_lang = request.form.get('source_lang')
        trg_lang = request.form.get('target_lang')
        corpus = request.form.get('corpus')

        src_lang_code_custom = request.form.get('source_lang_code_custom')
        src_lang_name_custom = request.form.get('source_lang_name_custom')

        trg_lang_code_custom = request.form.get('target_lang_code_custom')
        trg_lang_name_custom = request.form.get('target_lang_name_custom')

        # if either source or target custom language boxes have value,
        # set the real source/target with said value and add it to DB
        if src_lang_code_custom:
            src_lang = src_lang_code_custom
            custom_lang = user_utils.add_custom_language(src_lang_code_custom, src_lang_name_custom)

        if trg_lang_code_custom:
            trg_lang = trg_lang_code_custom
            custom_lang = user_utils.add_custom_language(trg_lang_code_custom, trg_lang_name_custom)

        data = requests.get(f"http://opus.nlpl.eu/opusapi/?corpus={corpus}&source={src_lang}&target={trg_lang}&preprocessing=moses&version=latest")
        output = data.json()
        
        url_to_download = output["corpora"][0]["url"]
        corpus_name = output["corpora"][0]["corpus"]

        USER_ID = user_utils.get_uid()
        source_lang_id = UserLanguage.query.filter_by(code=src_lang, user_id=USER_ID).one().id
        target_lang_id = UserLanguage.query.filter_by(code=trg_lang, user_id=USER_ID).one().id

        # Check if corpus has already been downloaded for the given source and target languages
        # to check if an OPUS corpus has already been downloaded by anyone
        # we have to use all the corpora with the given name and then 
        # check if the input src and trg languages are the same as
        # any of the corpora that are obtained by the query
        all_corpora = Corpus.query.filter_by(name=corpus_name).all()

        for corpus in all_corpora:
            if src_lang == corpus.source.code and trg_lang == corpus.target.code:
                db.session.remove()
                return jsonify({ "result": -1 })

        # if corpus doesn't exist in db, but there are folders/files with it, then delete them
        opus_workdir = app.config["OPUS_FILES_FOLDER"]
        aux_dir = f"{corpus_name}_{src_lang}-{trg_lang}"
        corpus_dir = os.path.join(opus_workdir, aux_dir)
        if os.path.isdir(corpus_dir):
            shutil.rmtree(corpus_dir)

        source_file = os.path.join(opus_workdir, aux_dir, f"prepared_corpus/{corpus_name}.{src_lang}-{trg_lang}.{src_lang}")
        target_file = os.path.join(opus_workdir, aux_dir, f"prepared_corpus/{corpus_name}.{src_lang}-{trg_lang}.{trg_lang}")

        # Launch bash scrip to download the corpus, paste the files, shuffle a new one,
        # delete the unwanted files, and split the shuffled file into two (src and trg)
        path_to_script = os.path.join(app.config['MUTNMT_FOLDER'], "app/blueprints/data/prepare_opus_corpus.sh")
        TEMP_LOG_FILE = os.path.join(opus_workdir, "TMP_FILE.txt")

        # Call asynchronous function to download and prepare the corpus
        task = tasks.download_opus_dataset.apply_async(args=[path_to_script, url_to_download, opus_workdir, src_lang, trg_lang, corpus_name, TEMP_LOG_FILE,
                                                                USER_ID, source_file, target_file, source_lang_id, target_lang_id, corpus_dir])

        return jsonify({ "result": 200, "task_id": task.id})
    except Exception as ex:
        print("Exception in download_opus_corpus: " + str(ex), flush = True)
        return jsonify({ "result": -2})
    

from celery import Celery

@data_blueprint.route('/check-downloading', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def check_downloading():
    try:
        task_id = request.form.get('task_id')

        res = AsyncResult(str(task_id), app=tasks.celery)
        state = res.state
        
        # Check if task exists
        if state is None:
            return jsonify({"result": 404})

        # Create celery instance for inspection
        celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"], 
                       backend=app.config["CELERY_RESULT_BACKEND"])
        
        # Get active workers and their tasks
        inspection = celery.control.inspect()
        active_workers = inspection.active()

        # Check if task is pending but not in active workers
        if state == 'PENDING':
            task_in_workers = False
            for worker_tasks in active_workers.values():
                for task in worker_tasks:
                    if task['id'] == task_id:
                        task_in_workers = True
                        break
                if task_in_workers:
                    break
            
            if not task_in_workers:
                return jsonify({"result": 200, "finished": True})

        # Check if task is finished
        finished = res.ready()

        return jsonify({ "result": 200, "finished": finished})
    except Exception as ex:
        print("Exception in check_downloading: " + str(ex), flush = True)
        return jsonify({ "result": -1})

from flask import session

@data_blueprint.route('/set-session-data', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def set_session_data():
    try:
        task_id = request.form.get('task_id')
        dataset = request.form.get('dataset')

        # Store data in session
        session["pending_download"] = task_id
        session["dataset"] = dataset
        
        return jsonify({ "result": 200})
    except Exception as ex:
        print("Exception in set_session_data: " + str(ex), flush = True)
        return jsonify({ "result": -1})

@data_blueprint.route('/get-session-data', methods=['GET'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def get_session_data():
    try:
        return jsonify({ "result": 200, "pending_download": session["pending_download"], "dataset": session["dataset"]})
    except Exception as ex:
        print("Exception in get_session_data: " + str(ex), flush = True)
        return jsonify({ "result": -1})
