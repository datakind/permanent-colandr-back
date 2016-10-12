from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants
from ...models import db, Fulltext  # , FulltextExtractedData
from ..errors import no_data_found, unauthorized
from ..schemas import FulltextExtractedDataSchema
from ..authentication import auth


class FulltextExtractedDataResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        })
    def get(self, id):
        # check current user authorization
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get extracted data for this fulltext'.format(
                    g.current_user))
        return FulltextExtractedDataSchema().dump(fulltext.extracted_data).data

    # NOTE: since extracted data are created automatically upon fulltext inclusion
    # and deleted automatically upon fulltext exclusion, "delete" here amounts
    # to nulling out its non-required fields
    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        # check current user authorization
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get extracted data for this fulltext'.format(
                    g.current_user))
        extracted_data = fulltext.extracted_data
        extracted_data.extracted_data = {}
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return '', 204

    @swagger.operation()
    @use_args(FulltextExtractedDataSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        # check current user authorization
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get extracted data for this fulltext'.format(
                    g.current_user))
        extracted_data = fulltext.extracted_data
        if not extracted_data:
            return no_data_found(
                '<FulltextExtractedData(fulltext_id={})> not found'.format(id))
        # TODO: validation of data based on ReviewPlan.data_extraction_form
        import logging
        logging.critical('BURTON: finish PUT => FulltextExtractedDataResource!')
        # for key, value in args.items():
        #     if key is missing:
        #         continue
        #     else:
        #         setattr(review_plan, key, value)
        # if test is False:
        #     db.session.commit()
        # else:
        #     db.session.rollback()
        return FulltextExtractedDataSchema().dump(extracted_data).data
