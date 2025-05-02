import hashlib
import ntpath
import os
import re
import shutil
import sys
from datetime import datetime
from functools import reduce
from sqlalchemy.orm.exc import NoResultFound
import iso639
import pytz
from dateutil import tz
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, not_
from sqlalchemy.orm import load_only

from app import app, db
from app.flash import Flash
from app.models import (
    Corpus,
    Corpus_Engine,
    Corpus_File,
    Engine,
    File,
    Language,
    LibraryCorpora,
    LibraryEngine,
    Resource,
    Topic,
    User,
    UserLanguage,
)
from app.utils import datatables, tensor_utils, training_log, user_utils, utils
from app.utils.power import PowerUtils
from app.utils.roles import EnumRoles
from app.utils.user_utils import is_admin, is_expert

library_blueprint = Blueprint("library", __name__, template_folder="templates")
import io
import yaml
import zipfile
import requests

from app.utils.opus_models import get_opus_model_info
from app.utils.user_utils import get_user


@library_blueprint.route('/corpora')
def library_corpora():
    user_library = user_utils.get_user_corpora().count()
    public_files = user_utils.get_user_corpora(public=True).count()
    used_library = user_utils.get_user_corpora(used=True).count() if is_admin() else 0
    not_used_library = user_utils.get_user_corpora(not_used=True).count() if is_admin() else 0

    languages = UserLanguage.query.filter_by(user_id=current_user.id).order_by(UserLanguage.name).all()
    topics = Topic.query.all()
    role_with_access = is_admin() or is_expert()
    return render_template('library_corpora.html.jinja2', page_name='library_corpora', page_title='Datasets',
                           user_library=user_library, public_files = public_files, languages=languages, topics=topics,
                           used_library=used_library, not_used_library=not_used_library, role_with_access= role_with_access)


@library_blueprint.route("/engines")
def library_engines():
    user_library = User.query.filter_by(id=user_utils.get_uid()).first().user_engines
    public_engines = Engine.query.filter_by(public=True)

    user_engines = list(map(lambda l: l.engine, user_library))
    for engine in public_engines:
        engine.grabbed = engine in user_engines
    role_with_access = is_admin() or is_expert()
    return render_template(
        "library_engines.html.jinja2",
        page_name="library_engines",
        page_title="Engines",
        user_library=user_library,
        public_engines=public_engines,
        role_with_access=role_with_access,
    )


@library_blueprint.route("/corpora_feed", methods=["POST"])
def library_corpora_feed():
    public = request.form.get("public") == "true"
    used = request.form.get("used") == "true"
    not_used = request.form.get("not_used") == "true"

    print("BEING CALLED OVER HERE*************")

    if public:
        library_objects = user_utils.get_user_corpora(public=True).all()
    elif used:
        library_objects = user_utils.get_user_corpora(used=True).all()
    elif not_used:
        library_objects = user_utils.get_user_corpora(not_used=True).all()
    else:
        library_objects = user_utils.get_user_corpora().all()

    user_library = [lc.corpus for lc in library_objects]

    # We are not using the datatables helper since this is an specific case
    # and we need more control to group corpora

    draw = int(request.form.get("draw"))
    search = request.form.get("search[value]")
    start = int(request.form.get("start"))
    length = int(request.form.get("length"))
    order = int(request.form.get("order[0][column]"))
    dir = request.form.get("order[0][dir]")

    corpus_rows = []
    for corpus in user_library:
        corpus_rows.append(
            [
                corpus.id,
                corpus.name,
                corpus.source.name + (corpus.target.name if corpus.target else ""),
                corpus.lines(),
                corpus.words(),
                corpus.chars(),
                corpus.uploaded(),
            ]
        )

    recordsTotal = len(corpus_rows)
    recordsFiltered = 0

    if order:
        corpus_rows.sort(key=lambda c: c[order], reverse=(dir == "asc"))

    if start is not None and length is not None:
        corpus_rows = corpus_rows[start : (start + length)]

    corpus_data = []
    for row in corpus_rows:
        corpus = Corpus.query.filter_by(id=row[0]).first()

        file_entries = corpus.corpus_files
        file_entries.sort(key=lambda f: f.role)

        file_data = []
        for file_entry in file_entries:
            file = file_entry.file
            uploaded_date = datetime.fromtimestamp(datetime.timestamp(file.uploaded)).strftime("%d/%m/%Y")
            file_data.append([
                file.id,
                file.name,
                file.language.name,
                utils.format_number(file.lines), 
                utils.format_number(file.words), 
                corpus.topic.name if corpus.topic else "",
                uploaded_date,
                {
                    "corpus_owner": file.uploader.id == user_utils.get_uid() if file.uploader else False,
                    "corpus_uploader": file.uploader.username if file.uploader else "MutNMT",
                    "corpus_id": corpus.id,
                    "user_is_admin": user_utils.is_admin(),
                    "opus_corpus": corpus.opus_corpus,
                    "corpus_name": corpus.name,
                    "corpus_description": corpus.description,
                    "corpus_source": corpus.source.name,
                    "corpus_target": corpus.target.name if corpus.target else "",
                    "corpus_public": corpus.public,
                    "corpus_size": corpus.corpus_files[0].file.lines,
                    "corpus_preview": url_for('library.corpora_preview', id = corpus.id),
                    "corpus_share": url_for('library.library_share_toggle', type = 'library_corpora', id = corpus.id),
                    "corpus_delete": url_for('library.library_delete', id = corpus.id, type = 'library_corpora'),
                    "corpus_grab": url_for('library.library_grab', id = corpus.id, type = 'library_corpora'),
                    "corpus_ungrab": url_for('library.library_ungrab', id = corpus.id, type = 'library_corpora'),
                    "corpus_export": url_for('library.library_export', id= corpus.id, type = "library_corpora"),
                    "file_preview": url_for('data.data_preview', file_id=file.id)
                }
            ])

        if search:
            found = False
            for col in row + file_data:
                found = found or (search.lower() in str(col).lower())

            if found:
                corpus_data = corpus_data + file_data
                recordsFiltered += 1
        else:
            corpus_data = corpus_data + file_data

    return jsonify(
        {
            "draw": draw + 1,
            "recordsTotal": recordsTotal,
            "recordsFiltered": recordsFiltered if search else recordsTotal,
            "data": corpus_data,
        }
    )


@library_blueprint.route("/engines_feed", methods=["POST"])
def library_engines_feed():
    public = request.form.get("public") == "true"
    columns = [
        Engine.id,
        Engine.name,
        Engine.description,
        Engine.source_id,
        Engine.uploaded,
        Engine.uploader_id,
    ]
    dt = datatables.Datatables()

    rows, rows_filtered, search = dt.parse(
        Engine,
        columns,
        request,
        (
            and_(
                Engine.public == True,
                not_(
                    Engine.engine_users.any(
                        LibraryEngine.user_id == user_utils.get_uid()
                    )
                ),
            )
            if public
            else Engine.engine_users.any(LibraryEngine.user_id == user_utils.get_uid())
        ),
    )

    engine_data = []
    for engine in rows_filtered if search else rows:
        # We try to get BLEU score for this engine
        score = None
        try:
            with open(os.path.join(engine.model_path, "train.log"), "r") as log_file:
                for line in log_file:
                    groups = re.search(
                        training_log.validation_regex, line, flags=training_log.re_flags
                    )
                    if groups:
                        if groups.groups()[5] == "bleu":
                            bleu_score = float(groups.groups()[6])
                            score = (
                                bleu_score
                                if score is None or bleu_score > score
                                else score
                            )
        except IOError:
            pass

        uploaded_date = datetime.fromtimestamp(datetime.timestamp(engine.uploaded)).strftime("%d/%m/%Y")
        engine_data.append([engine.id, engine.name, engine.description, "{} — {}".format(engine.source.name, engine.target.name),
                            uploaded_date, engine.uploader.username if engine.uploader else "OPUS" if engine.opus_engine else "MutNMT", score, "",
                            {
                                "engine_owner": engine.uploader.id == user_utils.get_uid() if engine.uploader else False,
                                "engine_public": engine.public,
                                "opus_engine": engine.opus_engine,
                                "user_is_admin": user_utils.is_admin(),
                                "engine_status": engine.status,
                                "engine_share": url_for('library.library_share_toggle', type = "library_engines", id = engine.id),
                                "engine_summary": url_for('train.train_console', id = engine.id),
                                "engine_delete": url_for('library.library_delete', id = engine.id, type = "library_engines"),
                                "engine_grab": url_for('library.library_grab', id = engine.id, type = "library_engines"),
                                "engine_ungrab": url_for('library.library_ungrab', id = engine.id, type = "library_engines"),
                                "engine_export": url_for('library.library_export', id = engine.id, type = "library_engines"),
                                "engine_corpora_export": url_for('library.library_corpora_export', id = engine.id),
                                "engine_test_score": -1 if engine.test_score is None else engine.test_score
                            }])

        order = int(request.form.get('order[0][column]'))
        direction = request.form.get('order[0][dir]')

        if order == 6:
            # Order by bleu
            engine_data.sort(
                key=lambda c: c[order] if c[order] else 0, reverse=(direction == "asc")
            )

    return dt.response(rows, rows_filtered, engine_data)


@library_blueprint.route("/preview/<id>")
def corpora_preview(id):
    try:
        corpus = Corpus.query.filter_by(id=id).first()
        return render_template(
            "library_preview.html.jinja2",
            page_name="library_corpora_preview",
            corpus=corpus,
        )
    except:
        Flash.issue("Preview is currently unavailable", Flash.ERROR)
        return render_template(request.referrer)


@library_blueprint.route("/stream", methods=["POST"])
def stream_file():
    file_id = request.form.get("file_id")

    try:
        start = int(request.form.get("start"))
        offset = int(request.form.get("offset"))

        file = File.query.filter_by(id=file_id).first()
        lines = [line for line in utils.file_reader(file.path, start, offset)]
        return jsonify({"result": 200, "lines": lines})
    except:
        return jsonify({"result": -1, "lines": []})


@library_blueprint.route("/share/<type>/<id>")
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_share_toggle(type, id):
    if type == "library_corpora":
        db_resource = Corpus.query.filter_by(
            owner_id=user_utils.get_uid(), id=id
        ).first()
        db_resource.public = not db_resource.public
        db.session.commit()
    else:
        db_resource = Engine.query.filter_by(
            uploader_id=user_utils.get_uid(), id=id
        ).first()
        db_resource.public = not db_resource.public
        db.session.commit()

    return redirect(request.referrer)


@library_blueprint.route("/grab/<type>/<id>")
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_grab(type, id):
    user = User.query.filter_by(id=user_utils.get_uid()).first()

    if type == "library_corpora":
        corpus = Corpus.query.filter_by(id=id).first()
        user.user_corpora.append(LibraryCorpora(corpus=corpus, user=user))
        # If user doesn't have any of the corpus langs, add them
        if not UserLanguage.query.filter_by(
            code=corpus.source.code, user_id=current_user.id
        ).first():
            user_utils.add_custom_language(corpus.source.code, corpus.source.name)
        if not UserLanguage.query.filter_by(
            code=corpus.target.code, user_id=current_user.id
        ).first():
            user_utils.add_custom_language(corpus.target.code, corpus.target.name)
    else:
        engine = Engine.query.filter_by(id=id).first()
        user.user_engines.append(LibraryEngine(engine=engine, user=user))

    db.session.commit()

    return redirect(request.referrer)


@library_blueprint.route("/remove/<type>/<id>")
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_ungrab(type, id):
    user = User.query.filter_by(id=user_utils.get_uid()).first()

    if type == "library_corpora":
        library = LibraryCorpora.query.filter_by(
            corpus_id=id, user_id=user_utils.get_uid()
        ).first()
        user.user_corpora.remove(library)
    else:
        library = LibraryEngine.query.filter_by(
            engine_id=id, user_id=user_utils.get_uid()
        ).first()
        user.user_engines.remove(library)

    db.session.commit()

    return redirect(request.referrer)


@library_blueprint.route("/delete/<type>/<id>")
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_delete(type, id):
    user_utils.library_delete(type, id)

    return redirect(request.referrer)


@library_blueprint.route("/export/<type>/<id>")
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_export(type, id):
    zip_path = None

    if type == "library_engines":
        engine = Engine.query.filter_by(id=id).first()
        zip_path = os.path.join(
            app.config["TMP_FOLDER"], "engine-{}.mut".format(engine.id)
        )
        shutil.make_archive(zip_path, "zip", engine.path, ".")
    else:
        tmp_folder = utils.tmpfolder()
        corpus = Corpus.query.filter_by(id=id).first()
        for file_entry in corpus.corpus_files:
            filename = ntpath.basename(file_entry.file.path)
            shutil.copy(
                file_entry.file.path, os.path.join(tmp_folder, file_entry.file.name)
            )
        zip_path = os.path.join(
            app.config["TMP_FOLDER"], "corpus-{}.mut.zip".format(corpus.id)
        )
        shutil.make_archive(zip_path, "zip", tmp_folder, ".")
        shutil.rmtree(tmp_folder)

    return send_file(zip_path + ".zip", as_attachment=True)


@library_blueprint.route("/export-corpora/<id>")
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_corpora_export(id):
    """
    Decodes corpora of engine with ID :id, zips everything
    and serves it as a download
    """

    zip_path = None
    tmp_folder = utils.tmpfolder()

    corpora = Corpus_Engine.query.filter_by(engine_id=id, is_info=False).all()
    for corpus_entry in corpora:
        suffix = "{}-{}".format(
            corpus_entry.corpus.source.code, corpus_entry.corpus.target.code
        )
        for file_entry in corpus_entry.corpus.corpus_files:
            filename = "{}.{}.{}".format(
                corpus_entry.phase,
                suffix,
                (
                    corpus_entry.corpus.source.code
                    if file_entry.role == "source"
                    else corpus_entry.corpus.target.code
                ),
            )
            shutil.copy(file_entry.file.path, os.path.join(tmp_folder, filename))

    zip_path = os.path.join(
        app.config["TMP_FOLDER"], "engine-corpora-{}.mut.zip".format(id)
    )
    shutil.make_archive(zip_path, "zip", tmp_folder, ".")
    shutil.rmtree(tmp_folder)

    return send_file(zip_path + ".zip", as_attachment=True)


def _validate_and_convert_langs(src_lang, trg_lang):
    """Validate and convert the language codes to ISO 639-3 language objects."""
    try:
        iso_src_lang = iso639.Lang(src_lang)
        iso_trg_lang = iso639.Lang(trg_lang)
        if src_lang != iso_src_lang.pt1 or trg_lang != iso_trg_lang.pt1:
            raise ValueError("Provided language codes are not in ISO 639-1 format")
        src_alpha_3 = iso_src_lang.pt3
        trg_alpha_3 = iso_trg_lang.pt3
        return src_alpha_3, trg_alpha_3
    except iso639.exceptions.InvalidLanguageValue:
        raise ValueError("Languages are not valid")
    
@library_blueprint.route("/get-model", methods=["POST"])
def get_model():
    """Get info and download link for an OPUS model given a source and target language."""
    src_lang = request.form.get("source_lang")
    trg_lang = request.form.get("target_lang")
    try:
        src_alpha_3, trg_alpha_3 = _validate_and_convert_langs(src_lang, trg_lang)
        model_info = get_opus_model_info(src_alpha_3, trg_alpha_3)
        return model_info
    except ValueError as e:
        return jsonify({"result": -1, "info": str(e)})

@library_blueprint.route("/download-model", methods=["POST"])
def download_model():
    """Download an OPUS model given a source and target language.
    
    Note: This is a draft implementation and it may change.
    """
    src_lang = request.form.get("source_lang")
    trg_lang = request.form.get("target_lang")
    try:
        src_alpha_3, trg_alpha_3 = _validate_and_convert_langs(src_lang, trg_lang)
    except ValueError as e:
        return jsonify({"result": -1, "info": str(e)})
    engine_path = os.path.join(
        app.config["PRELOADED_ENGINES_FOLDER"], f"{src_lang}-{trg_lang}"
    )
    source_lang_db = UserLanguage.query.filter_by(code=src_lang, user_id=-1).first()
    target_lang_db = UserLanguage.query.filter_by(code=trg_lang, user_id=-1).first()
    if source_lang_db and target_lang_db:
        model_exists = Engine.query.filter_by(user_source_id=source_lang_db.id, 
                                        user_target_id=target_lang_db.id,
                                        opus_engine=True).first()
        if model_exists:
            return jsonify({"result": 200, "info": "Model already exists"})

    model_link = None
    try:
        model_link = get_opus_model_info(src_alpha_3, trg_alpha_3)["download_link"]
        model_path = os.path.join(engine_path, "model")
        os.makedirs(engine_path)
    except ValueError as e:
        return jsonify({"result": -1, "info": str(e)})
  
    try:
        r = requests.get(model_link, timeout=100, stream=True)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(model_path)
    except Exception as e:
        return jsonify({"result": -1, "info": "Model could not be downloaded or extracted"})
    
    try:
        date = datetime.now().replace(second=0, microsecond=0)
        engine = Engine(
            name=f"opus-{src_lang}-{trg_lang}",
            path=engine_path,
            model_path=model_path,
            opus_engine=True,
            description="Model downloaded from the OPUS repository.",
            user_source_id=source_lang_db.id,
            user_target_id=target_lang_db.id,
            public=True,
            launched=date,
            finished=date,
            status="opus"
        )
        db.session.add(engine)
        db.session.commit()

        # open the decoder yaml file, get the vocabulary name/path
        # and change the file's name/path to source and target equivalents
        with open(os.path.join(engine.model_path, "decoder.yml"), "r") as f:
            decoder_config = yaml.safe_load(f)
        
        src_vocab_path = os.path.join(engine.model_path, decoder_config["vocabs"][0])
        trg_vocab_path = os.path.join(engine.model_path, decoder_config["vocabs"][1])

        shutil.move(src_vocab_path, os.path.join(engine.model_path, f"vocab.{src_lang}.yml"))

        if src_vocab_path != trg_vocab_path:
            shutil.move(trg_vocab_path, os.path.join(engine.model_path, f"vocab.{trg_lang}.yml"))
        else:
            shutil.copy2(os.path.join(engine.model_path, f"vocab.{src_lang}.yml"), 
                            os.path.join(engine.model_path, f"vocab.{trg_lang}.yml"))

        return jsonify({"result": 200})
    except Exception as ex:
        print(str(ex), flush=True)
        return jsonify({"result": -1, "info": str(ex)})