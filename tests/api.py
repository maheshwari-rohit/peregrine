import os
import string
import sys

from elasticsearch import ElasticsearchException, Elasticsearch
import flask
from flask import Flask, jsonify
from flask.ext.cors import CORS
from flask_sqlalchemy_session import flask_scoped_session
from psqlgraph import PsqlGraphDriver

from dictionaryutils import DataDictionary, dictionary as dict_init
import datamodelutils
from peregrine import dictionary
from datamodelutils import models, validators
from indexclient.client import IndexClient as SignpostClient
from userdatamodel.driver import SQLAlchemyDriver

import cdis_oauth2client
from cdis_oauth2client import OAuth2Client, OAuth2Error
from cdisutils.log import get_handler

import peregrine
from peregrine import blueprints

from peregrine.auth import AuthDriver
from peregrine.config import LEGACY_MODE
from peregrine.errors import APIError, setup_default_handlers, UnhealthyCheck
from peregrine.resources import submission
from peregrine.version_data import VERSION, COMMIT, DICTVERSION, DICTCOMMIT


# recursion depth is increased for complex graph traversals
sys.setrecursionlimit(10000)
DEFAULT_ASYNC_WORKERS = 8


def app_register_blueprints(app):
    # TODO: (jsm) deprecate the index endpoints on the root path,
    # these are currently duplicated under /index (the ultimate
    # path) for migration
    v0 = '/v0'
    app.url_map.strict_slashes = False

    import sheepdog
    import gdcdictionary
    import gdcdatamodel
    sheepdog_blueprint = sheepdog.blueprint.create_blueprint(
        gdcdictionary.gdcdictionary, gdcdatamodel.models
    )

    app.register_blueprint(sheepdog_blueprint, url_prefix=v0+'/submission')

    app.register_blueprint(peregrine.blueprints.blueprint, url_prefix=v0+'/submission')
    app.register_blueprint(cdis_oauth2client.blueprint, url_prefix=v0+'/oauth2')


def app_register_duplicate_blueprints(app):
    # TODO: (jsm) deprecate this v0 version under root endpoint.  This
    # root endpoint duplicates /v0 to allow gradual client migration
    app.register_blueprint(peregrine.blueprints.blueprint, url_prefix='/submission')


def async_pool_init(app):
    """Create and start an pool of workers for async tasks."""
    n_async_workers = (
        app.config
        .get('ASYNC', {})
        .get('N_WORKERS', DEFAULT_ASYNC_WORKERS)
    )
    app.async_pool = peregrine.utils.scheduling.AsyncPool()
    app.async_pool.start(n_async_workers)


def db_init(app):
    app.logger.info('Initializing PsqlGraph driver')
    app.db = PsqlGraphDriver(
        host=app.config['PSQLGRAPH']['host'],
        user=app.config['PSQLGRAPH']['user'],
        password=app.config['PSQLGRAPH']['password'],
        database=app.config['PSQLGRAPH']['database'],
        set_flush_timestamps=True,
    )

    app.userdb = SQLAlchemyDriver(app.config['PSQL_USER_DB_CONNECTION'])
    flask_scoped_session(app.userdb.Session, app)

    app.oauth2 = OAuth2Client(**app.config['OAUTH2'])

    app.logger.info('Initializing Signpost driver')
    app.signpost = SignpostClient(
        app.config['SIGNPOST']['host'],
        version=app.config['SIGNPOST']['version'],
        auth=app.config['SIGNPOST']['auth'])
    try:
        app.logger.info('Initializing Auth driver')
        app.auth = AuthDriver(app.config["AUTH_ADMIN_CREDS"], app.config["INTERNAL_AUTH"])
    except Exception:
        app.logger.exception("Couldn't initialize auth, continuing anyway")


def es_init(app):
    app.logger.info('Initializing Elasticsearch driver')
    app.es = Elasticsearch([app.config["GDC_ES_HOST"]],
                           **app.config["GDC_ES_CONF"])


# Set CORS options on app configuration
def cors_init(app):
    accepted_headers = [
        'Content-Type',
        'X-Requested-With',
        'X-CSRFToken',
    ]
    CORS(app, resources={
        r"/*": {"origins": '*'},
        }, headers=accepted_headers, expose_headers=['Content-Disposition'])

def dictionary_init(app):
    dictionary_url = app.config.get('DICTIONARY_URL')
    if dictionary_url:
        app.logger.info('Initializing dictionary from url')
        d = DataDictionary(url=dictionary_url)
        dict_init.init(d)
        dictionary.init(d)
    else:
        app.logger.info('Initializing dictionary from gdcdictionary')
        from gdcdictionary import gdcdictionary
        dictionary.init(gdcdictionary)
    from gdcdatamodel import models as md
    from gdcdatamodel import validators as vd
    datamodelutils.validators.init(vd)
    datamodelutils.models.init(md)

    from datamodelutils.models import *
    

def app_init(app):
    # Register duplicates only at runtime
    app.logger.info('Initializing app')
    dictionary_init(app)
    
    app_register_blueprints(app)
    # app_register_duplicate_blueprints(app)
    if LEGACY_MODE:
        app_register_legacy_blueprints(app)
        app_register_v0_legacy_blueprints(app)
    db_init(app)
    # exclude es init as it's not used yet
    # es_init(app)
    cors_init(app)
    app.graphql_schema = submission.graphql.get_schema()
    try:
        app.secret_key = app.config['FLASK_SECRET_KEY']
    except KeyError:
        app.logger.error(
            'Secret key not set in config! Authentication will not work'
        )
    # slicing.v0.config(app)
    async_pool_init(app)
    app.logger.info('Initialization complete.')

app = Flask(__name__)

# Setup logger
app.logger.addHandler(get_handler())

setup_default_handlers(app)

@app.route('/_status', methods=['GET'])
def health_check():
    with app.db.session_scope() as session:
        try:
            query = session.execute('SELECT 1')
        except Exception as e:
            raise UnhealthyCheck()

    return 'Healthy', 200

@app.route('/_version', methods=['GET'])
def version():
    dictver = {
        'version': DICTVERSION,
        'commit': DICTCOMMIT,
    }
    base = {
        'version': VERSION,
        'commit': COMMIT,
        'dictionary': dictver,
    }

    return jsonify(base), 200

@app.errorhandler(404)
def page_not_found(e):
    return jsonify(message=e.description), e.code


@app.errorhandler(500)
def server_error(e):
    app.logger.exception(e)
    return jsonify(message="internal server error"), 500


def _log_and_jsonify_exception(e):
    """
    Log an exception and return the jsonified version along with the code.

    This is the error handling mechanism for ``APIErrors`` and
    ``OAuth2Errors``.
    """
    app.logger.exception(e)
    if hasattr(e, 'json') and e.json:
        return jsonify(**e.json), e.code
    else:
        return jsonify(message=e.message), e.code

app.register_error_handler(APIError, _log_and_jsonify_exception)

import peregrine.errors
app.register_error_handler(
    peregrine.errors.APIError, _log_and_jsonify_exception
)
app.register_error_handler(OAuth2Error, _log_and_jsonify_exception)


def run_for_development(**kwargs):
    import logging
    app.logger.setLevel(logging.INFO)
    # app.config['PROFILE'] = True
    # from werkzeug.contrib.profiler import ProfilerMiddleware, MergeStream
    # f = open('profiler.log', 'w')
    # stream = MergeStream(sys.stdout, f)
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, f, restrictions=[2000])

    for key in ["http_proxy", "https_proxy"]:
        if os.environ.get(key):
            del os.environ[key]
    app.config.from_object('peregrine.dev_settings')

    kwargs['port'] = app.config['PEREGRINE_PORT']
    kwargs['host'] = app.config['PEREGRINE_HOST']

    try:
        app_init(app)
    except:
        app.logger.exception(
            "Couldn't initialize application, continuing anyway"
        )
    app.run(**kwargs)
