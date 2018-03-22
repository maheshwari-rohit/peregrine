import os
from boto.s3.connection import OrdinaryCallingFormat
from os import environ as env

# Auth
AUTH = 'https://gdc-portal.nci.nih.gov/auth/keystone/v3/'
INTERNAL_AUTH = env.get('INTERNAL_AUTH', 'https://gdc-portal.nci.nih.gov/auth/')

AUTH_ADMIN_CREDS = {
    'domain_name': env.get('KEYSTONE_DOMAIN'),
    'username': env.get('KEYSTONE_USER'),
    'password': env.get('KEYSTONE_PASSWORD'),
    'auth_url': env.get('KEYSTONE_AUTH_URL'),
    'user_domain_name': env.get('KEYSTONE_DOMAIN')}

# Storage
CLEVERSAFE_HOST = env.get('CLEVERSAFE_HOST', 'cleversafe.service.consul')

STORAGE = {"s3": {
    "keys": {
        "cleversafe.service.consul": {
            "access_key": os.environ.get('CLEVERSAFE_ACCESS_KEY'),
            'secret_key': os.environ.get('CLEVERSAFE_SECRET_KEY')},
        "localhost": {
            "access_key": os.environ.get('CLEVERSAFE_ACCESS_KEY'),
            'secret_key': os.environ.get('CLEVERSAFE_SECRET_KEY')},
    }, "kwargs": {
        'cleversafe.service.consul': {
            'host': 'cleversafe.service.consul',
            "is_secure": False,
            "calling_format": OrdinaryCallingFormat()},
        'localhost': {
            'host': 'localhost',
            "is_secure": False,
            "calling_format": OrdinaryCallingFormat()},
    }}}
SUBMISSION = {
    "bucket": 'test_submission',
    "host": CLEVERSAFE_HOST,
}
# Postgres
PSQLGRAPH = {
    'host': os.getenv("GDC_PG_HOST", "localhost"),
    'user': os.getenv("GDC_PG_USER", "test"),
    'password': os.getenv("GDC_PG_PASSWORD", "test"),
    'database': os.getenv("GDC_PG_DBNAME", "sheepdog_automated_test")
}

PSQL_USER_DB_NAME = 'fence_test'
PSQL_USER_DB_USERNAME = 'test'
PSQL_USER_DB_PASSWORD = 'test'
PSQL_USER_DB_HOST = 'localhost'

PSQL_USER_DB_CONNECTION = "postgresql://{name}:{password}@{host}/{db}".format(
    name=PSQL_USER_DB_USERNAME, password=PSQL_USER_DB_PASSWORD, host=PSQL_USER_DB_HOST, db=PSQL_USER_DB_NAME
)

# API server
PEREGRINE_HOST = os.getenv("PEREGRINE_HOST", "localhost")
PEREGRINE_PORT = int(os.getenv("PEREGRINE_PORT", "5555"))

# FLASK_SECRET_KEY should be set to a secure random string with an appropriate
# length; 50 is reasonable. For the random generation to be secure, use
# ``random.SystemRandom()``
FLASK_SECRET_KEY = 'eCKJOOw3uQBR5pVDz3WIvYk3RsjORYoPRdzSUNJIeUEkm1Uvtq'

DICTIONARY_URL = os.environ.get('DICTIONARY_URL','https://s3.amazonaws.com/dictionary-artifacts/datadictionary/develop/schema.json')

OIDC_ISSUER = 'http://localhost/user'

HMAC_ENCRYPTION_KEY = os.environ.get('CDIS_HMAC_ENCRYPTION_KEY', '')
#OAUTH2 = {
#    "client_id": os.environ.get('CDIS_PEREGRINE_CLIENT_ID'),
#    "client_secret": os.environ.get("CDIS_PEREGRINE_CLIENT_SECRET"),
#    "oauth_provider": os.environ.get("CDIS_USER_API_OAUTH", 'http://localhost:8000/oauth2/'),
#    "redirect_uri": os.environ.get("CDIS_PEREGRINE_OAUTH_REDIRECT", 'localhost:5000/v0/oauth2/authorize'),
#}

OAUTH2 = {
    'client_id': '',
    'client_secret': '',
    'api_base_url': 'http://localhost/user/',
    'authorize_url': 'http://localhost/user/oauth2/authorize',
    'access_token_url': 'http://localhost0/user/oauth2/token',
    'refresh_token_url': 'http://localhost/user/oauth2/token',
    'client_kwargs': {
        'redirect_uri': 'http://localhost/api/v0/oauth2/authorize',
        'scope': 'openid data user',
    },
    # deprecated key values, should be removed after all commons use new oidc
    'internal_oauth_provider': 'http://localhost/oauth2/',
    'oauth_provider': 'http://localhost/user/oauth2/',
    'redirect_uri': 'http://localhost/api/v0/oauth2/authorize'
}

USER_API = "http://localhost:8000/"
SESSION_COOKIE_NAME = 'PEREGRINE_session'
# verify project existence in dbgap or not
VERIFY_PROJECT = False
AUTH_SUBMISSION_LIST = False
