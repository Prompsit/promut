import os
import json

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    BASEDIR = basedir
    MUTNMT_FOLDER = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
    TMP_FOLDER = '/tmp'
    LIST_FOLDER = os.path.join(basedir, 'list')
    PRELOADED_ENGINES_FOLDER = os.path.join(basedir, "preloaded")
    JOEYNMT_FOLDER = os.path.join(basedir, "joeynmt")
    MARIAN_FOLDER = os.path.join(basedir, "marian")
    DATA_FOLDER = os.path.join(MUTNMT_FOLDER, "data")
    USERSPACE_FOLDER = os.path.join(DATA_FOLDER, "userspace")
    STORAGE_FOLDER = os.path.join(USERSPACE_FOLDER, "storage")
    FILES_FOLDER = os.path.join(STORAGE_FOLDER, "files")
    OPUS_FILES_FOLDER = os.path.join(STORAGE_FOLDER, "opus_files")
    ENGINES_FOLDER = os.path.join(STORAGE_FOLDER, "engines")
    USERS_FOLDER = os.path.join(USERSPACE_FOLDER, "users")
    BASE_CONFIG_FOLDER = os.path.join(basedir, "base")
    EVALUATORS_FOLDER = os.path.join(BASEDIR, "blueprints/evaluate/evaluators")

    # This variable is used throughout the code to enable preprocessing and postprocessing of data
    # in the same way that people at OPUS do for their own models' input/output. Also used for
    # selecting how the vocab is created, either using sentencepiece or OPUS way.
    USE_OPUS_HANDLING = True

    INFIX = '.min' if os.environ.get('DEBUG') is None else ''

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(DATA_FOLDER, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "timeout": 30,
            "check_same_thread": False
        }
    }
    SQLALCHEMY_SESSION_OPTIONS = {
        "autoflush": False
    }

    SECRET_KEY = 'development key' # change by your own
    DEBUG      = False

    # Uncomment it to enable translations. Follow instructions in README.md to add more languages
    LANGUAGES = { 'ca': 'Català', 'en': 'English', 'es': 'Spanish' }

    ADMIN_EMAIL = ""

    USER_LOGIN_ENABLED          = True
    ENABLE_NEW_LOGINS           = True
    USER_WHITELIST_ENABLED      = True
    BANNED_USERS                = []
    OAUTHLIB_INSECURE_TRANSPORT = True # True also behind firewall,  False -> require HTTPS

    #with open(os.path.join(BASE_CONFIG_FOLDER, "client-secret.json"), "r") as file:
    #    data = json.load(file)

    #GOOGLE_OAUTH_CLIENT_ID      = data["web"]["client_id"]
    #GOOGLE_OAUTH_CLIENT_SECRET  = data["web"]["client_secret"]
    GOOGLE_USER_DATA_URL        = '/oauth2/v1/userinfo'
    USE_PROXY_FIX = True

    try:
        with open(os.path.join(LIST_FOLDER, 'admin.list'), 'r') as admin_file:
            ADMINS = [line.strip() for line in admin_file if line.strip() != ""]
    except Exception as ex:
        print("Exception in whitelist creation: " + str(ex), flush = True)
        ADMINS = []

    if USER_WHITELIST_ENABLED:
        try:
            with open(os.path.join(LIST_FOLDER, 'white.list'), 'r') as whitelist_file:
                WHITELIST = [line.strip() for line in whitelist_file if line.strip() != ""]
        except Exception as ex:
            print("Exception in whitelist creation: " + str(ex), flush = True)
            WHITELIST = None
    else:
        WHITELIST = None
    
    # Celery
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
    CELERYD_CONCURRENCY = 4

    
