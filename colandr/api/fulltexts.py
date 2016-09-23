from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy import asc, desc, or_
from sqlalchemy.sql import operators

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Length, Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs
from werkzeug.utils import secure_filename

from ..lib import constants
from ..lib.parsers import BibTexFile, RisFile
from ..models import db, Fulltext, Review
from .errors import no_data_found, unauthorized, validation
from .schemas import FulltextSchema
from .authentication import auth


class FulltextResource(Resource):

    method_decorators = [auth.login_required]
