# SQLALCHEMY_DATABASE_URI config option must be an environment variable
# format: 'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
SECRET_KEY = 'bob-burton-caitlin-ray-sam'  # TODO: maybe move this to env var?
LOGGER_NAME = 'appname'
JSON_AS_ASCII = False
SQLALCHEMY_ECHO = True
SQLALCHEMY_TRACK_MODIFICATIONS = True
DEBUG = True
TESTING = False

# TODO: implement classes per config, e.g. Development vs Production
