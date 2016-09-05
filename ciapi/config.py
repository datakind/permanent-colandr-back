# SQLALCHEMY_DATABASE_URI config option: must be an environment variable
# format: 'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# COLANDR_SECRET_KEY config option: must be an environment variable
# treat it like a password, can be whatever, just make it hard to guess
LOGGER_NAME = 'colandr-api'
JSON_AS_ASCII = False
SQLALCHEMY_ECHO = True
SQLALCHEMY_TRACK_MODIFICATIONS = True
DEBUG = True
TESTING = False

# TODO: implement classes per config, e.g. Development vs Production?
