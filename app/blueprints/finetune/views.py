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

from app.blueprints.train.views import train_resume

finetune_blueprint = Blueprint('finetune', __name__, template_folder='templates')

@finetune_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_index():
    currently_finetuning = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("training")).all()

    if (len(currently_finetuning) > 0):
        return redirect(url_for('train.train_console', id=currently_finetuning[0].id))

    currently_launching = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("launching")).all()
                            
    if (len(currently_launching) > 0): 
        return redirect(url_for('train.train_launching', task_id=currently_launching[0].bg_task_id))

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
            return jsonify({ "result": -1 })
    else:
        return jsonify({ "result": -1 })
    
import pytz    

@finetune_blueprint.route('/launch', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def finetune_launch():
    id = request.form.get('engine_id')
    if user_utils.is_normal(): return url_for('index')

    # for the first ever finetuning of a model, the 'resume' function
    # from the training blueprint will be called
    # this function will create anything necessary and treat the model
    # as an already trained one 
    train_resume(id)

    return url_for('train.train_console', id=id)


@finetune_blueprint.route('/finetuning-failed')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def training_failed(task_id):
    if user_utils.is_normal(): return redirect(url_for('index'))

    return render_template('finetune_failed.html.jinja2', page_name='finetune', page_title='Finetuning failed')

@finetune_blueprint.route('/get-opus-models', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def get_opus_models():
    model_list = []
    print(f"", flush = True)
    print(f"---------------------------------", flush = True)

    try:
        USER_ID = user_utils.get_uid()
        user = User.query.filter_by(id=user_utils.get_uid()).first()

        src_lang = request.form.get("source_lang")
        trg_lang = request.form.get("target_lang")

        source_lang_db = UserLanguage.query.filter_by(code=src_lang, user_id=USER_ID).first()
        target_lang_db = UserLanguage.query.filter_by(code=trg_lang, user_id=USER_ID).first()

        # if languages exist
        if source_lang_db and target_lang_db:
            model_list_query = []
            # from engines the user has
            for user_engine in user.user_engines:
                engine = Engine.query.filter_by(id=user_engine.engine_id).first()
                
                source_l = UserLanguage.query.filter_by(id=engine.user_source_id).first()
                target_l = UserLanguage.query.filter_by(id=engine.user_target_id).first()
                
                # get all models that match the source and target codes 
                # check also if they are opus model and not already finetuned
                if source_l.code == src_lang and target_l.code == trg_lang:
                    if engine.opus_engine and not engine.finetuned:
                        model_list_query.append(engine)

            for model_obj in model_list_query:
                model_dict = {}
                model_dict["id"] = model_obj.id
                model_dict["name"] = model_obj.name
                model_list.append(model_dict)
                
    except Exception as e:
        return jsonify({"result": -1, "info": str(e)})

    return jsonify({"result": 200, "model_list": model_list})
