import flask_praetorian
from flask import current_app, g
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs

from ...lib import constants
from ...models import Fulltext, db
from ..errors import forbidden_error, not_found_error
from ..schemas import FulltextSchema


ns = Namespace("fulltexts", path="/fulltexts", description="get and delete fulltexts")


@ns.route("/<int:id>")
@ns.doc(
    summary="get and delete fulltexts",
    produces=["application/json"],
)
class FulltextResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of fulltext fields to return",
            },
        },
        responses={
            200: "successfully got fulltext record",
            403: "current app user forbidden to get fulltext record",
            404: "no fulltext with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            )
        },
        location="view_args",
    )
    @use_kwargs(
        {"fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None)},
        location="query",
    )
    def get(self, id, fields):
        """get record for a single fulltext by id"""
        current_user = flask_praetorian.current_user()
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return not_found_error("<Fulltext(id={})> not found".format(id))
        if (
            current_user.is_admin is False
            and fulltext.review.users.filter_by(id=current_user.id).one_or_none()
            is None
        ):
            return forbidden_error(
                "{} forbidden to get this fulltext".format(current_user)
            )
        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", fulltext)
        return FulltextSchema(only=fields).dump(fulltext)

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        responses={
            200: "request was valid, but record not deleted because `test=False`",
            204: "successfully deleted fulltext record",
            403: "current app user forbidden to delete fulltext record",
            404: "no fulltext with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @use_kwargs({"test": ma_fields.Boolean(load_default=False)}, location="query")
    def delete(self, id, test):
        """delete record for a single fulltext by id"""
        current_user = flask_praetorian.current_user()
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return not_found_error("<Fulltext(id={})> not found".format(id))
        if (
            current_user.is_admin is False
            and fulltext.review.users.filter_by(id=current_user.id).one_or_none()
            is None
        ):
            return forbidden_error(
                "{} forbidden to delete this fulltext".format(current_user)
            )
        db.session.delete(fulltext)
        if test is False:
            db.session.commit()
            current_app.logger.info("deleted %s", fulltext)
            return "", 204
        else:
            db.session.rollback()
            return "", 200
