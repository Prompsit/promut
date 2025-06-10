# ProMut

<img alt="ProMut Logo" src="app/static/img/logo.png" style="margin-bottom: 1rem;" height="75" />

ProMut aims to provide a web application to train neural machine translation with educational purposes. This web application lets the user train, inspect, evaluate and translate using neural engines. It has been cofunded by the European Union as part of the "LT-LiDER -- Language and Translation:
Literacy in digital environments and resources" project (grant number KA220-HED-15E72916).

ProMut is based on [MutNMT](https://github.com/Prompsit/mutnmt) which was developed inside the "MultiTraiNMT - Machine Translation training for multilingual citizens" European project (2019-1-ES01-KA203-064245, 01/09/2019–31/08/2022).

This application uses [MariaNTM](https://marian-nmt.github.io/) in its core.


## Features

ProMut preserves former MutNMT features and adds new ones:

* Upload and manage datasets
    * Upload datasets in text, TMX or TSV format
    * Tag datasets depending on domain
    * Share datasets with other users
    * NEW - Download datasets from the OPUS dataset repository
* Train and manage engines
    * Select datasets or a subset of those datasets and train a Transformer model
    * Track progress of the training process with data tables and charts
    * Stop and resume training at anytime
    * Manage, share and download engines
    * Inspect engines training log
    * NEW - Use MarianNMT instead of JoeyNMT as the core MT framework
    * NEW - Download Engines from OPUS-MT
* Translate text and documents
    * Select an already trained engine to translate text or documents (HTML, TMX, PDF and Office formats supported)
* Inspect an engine
    * Explore details on tokenization, candidate selection and pre-processed output
    * NEW - Know how to reuse engines in OPUS-CAT
* Evaluate translations
    * Upload parallel translation files to evaluate them using BLEU, chrF3, TER and TTR metrics
    * NEW Added COMET as a new metric
 


## Requisites

ProMut is provided as a [Docker](https://www.docker.com/) container. This container is based on [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker).

In order to run ProMut, you need access to an NVIDIA GPU. You must install the [necessary drivers](https://github.com/NVIDIA/nvidia-docker/wiki/Frequently-Asked-Questions#how-do-i-install-the-nvidia-driver) on the host machine. Note that you do not need to install the CUDA Toolkit on the host system, but it should be compatible with CUDA 11+.

## Roadmap

Building and launching ProMut consists on:

1. Set up preloaded engines
2. Set up user authentication
3. Set up proxy fix
4. Set up user lists: admins and whitelist
5. Build the Docker image
6. Launch the container

## Building ProMut

The image for the ProMut container must be built taking into account the following steps.

### Preloaded engines

You can build ProMut with preloaded engines so that users have something to translate and inspect with. Before building the Docker image, include the engines you want to preload in the `app/preloaded` folder.

Create the `app/preloaded` folder even if you don't want to include any preloaded engines. This folder is ignored by Docker in order to make build process faster and the image smaller, so it is mounted by default as a volume.

Engines must be Transformer-based, and must have been trained with [MarianNMT](https://marian-nmt.github.io/)), or preferably downloaded from OPUS.
ProMut will use the `model/train.log` to retrieve information about the engine, so make sure that file is available.

Each engine must be stored in its own folder, this is an example of an `app/preloaded` tree with one preloaded engine:

```
+ app/
|   + preloaded/
|   |   + transformer-en-es/
|   |   |    - config.yaml
|   |   |    - source.spm
|   |   |    - target.spm
|   |   |    - vocab.en.yml
|   |   |    - vocab.es.yml
|   |   |    + model/
|   |   |    |    - model.npz.yml
|   |   |    |    - model.npz.decoder.yml
|   |   |    |    - model.npz
|   |   |    |    - train.log
```

Any configuration files must have internal relative paths.

### Multiple user account setup

ProMut provides authentication based on the Google identity server through the OAUTH2 protocol. The procedure of setting such a server in the Google side is a bit complex and Google changes it from time to time, but it can be found [here](https://developers.google.com/identity/protocols/OAuth2UserAgent). Although not official, a useful resource is [this video](https://www.youtube.com/watch?v=A_5zc3DYZfs).

From the process above, you will get at the end a client secret `.json` file containing two strings: "client ID" and "client secret". This json file should be placed in the following path: `/app/base/client-secret.json`.

You can edit the config.py file if you want to change the files name, location, or set ID and secret manually:

```python
USER_LOGIN_ENABLED          = True
ENABLE_NEW_LOGINS           = True
USER_WHITELIST_ENABLED      = True
BANNED_USERS                = []
OAUTHLIB_INSECURE_TRANSPORT = True # True also behind firewall,  False -> require HTTPS

with open(os.path.join(BASE_CONFIG_FOLDER, "client-secret.json"), "r") as file:
    data = json.load(file)

GOOGLE_OAUTH_CLIENT_ID      = data["web"]["client_id"]
GOOGLE_OAUTH_CLIENT_SECRET  = data["web"]["client_secret"]
GOOGLE_USER_DATA_URL        = '/oauth2/v1/userinfo'
USE_PROXY_FIX = True
```

### Admin accounts

To specify admin accounts, please create a file in `app/lists` called `admin.list`, containing one administrator email per line. The admin accounts will allow you to use admin features. You can set as many as you want, and should always have at least one as you won't be able to change other users' roles.

### Whitelist

When user login is not enabled, a whitelist can be established to let the users in that list log in, but only them. This whitelist is only applied when `USER_LOGIN_ENABLED` is set to `False`. To specify a whitelist, create a file in `app/lists` called `white.list`, containing one user email per line. Then, enable the whitelist by setting `USER_WHITELIST_ENABLED` to `True`.

### Working behind a proxy

Google Authentication may fail to work under some scenarios, for example behind an HTTP proxy. Set `USE_PROXY_FIX` to `True` in order to enable [Proxy Fix](https://werkzeug.palletsprojects.com/en/1.0.x/middleware/proxy_fix/) and make authentication work behind a proxy.

### Good to go!

Once you are ready, build ProMut and run the container:

```
docker build -t promut .

docker-compose up -d
```

## Data persistance

Logs, database and user data like datasets or engines are stored inside the container in `/opt/promut/data`. This folder is mounted in `./data` by default, so that it persists in case of removing the container. Make sure to create the `./data` folder in the project's directory if it does not exist after running the container.
