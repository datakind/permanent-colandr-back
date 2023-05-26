from flask_restx import Api
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


api_ = Api(
    version="1.0",
    prefix="/api",
    doc="/docs",
    default_mediatype="application/json",
    title="colandr",
    description="REST API powering the colandr app",
)
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
