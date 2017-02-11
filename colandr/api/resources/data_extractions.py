import arrow

from flask import g
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants, sanitizers, utils
from ...models import db, DataExtraction, ReviewPlan, Study
from ..errors import forbidden, no_data_found, unauthorized, validation
from ..schemas import ExtractedItem, DataExtractionSchema
from ..swagger import extracted_item_model
from ..authentication import auth
from colandr import api_

logger = utils.get_console_logger(__name__)
ns = api_.namespace(
    'data_extractions', path='/data_extractions',
    description='get, delete, and modify data extractions')


@ns.route('/<int:id>')
@ns.doc(
    summary='get, delete, and modify data extractions',
    produces=['application/json'],
    )
class DataExtractionResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        responses={
            200: 'successfully got data extraction record',
            401: 'current app user not authorized to get data extraction record',
            404: 'no data extraction with matching id was found',
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        })
    def get(self, id):
        """get data extraction record for a single study by id"""
        # check current user authorization
        extracted_data = db.session.query(DataExtraction).get(id)
        if not extracted_data:
            return no_data_found(
                '<DataExtraction(study_id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                g.current_user.reviews.filter_by(id=extracted_data.review_id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get extracted data for this study'.format(
                    g.current_user))
        return DataExtractionSchema().dump(extracted_data).data

    @ns.doc(
        description='Since data extractions are automatically created upon fulltext inclusion and deleted upon fulltext exclusion, "delete" here amounts to nulling out some or all of its non-required fields',
        params={
            'labels': {'in': 'query', 'type': 'string',
                       'description': 'comma-delimited list-as-string of data extraction labels to "delete" (set to null)'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'request was valid, but record not deleted because `test=False`',
            204: 'successfully deleted (nulled) data extraction record',
            401: 'current app user not authorized to delete data extraction record',
            404: 'no data extraction with matching id was found',
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'labels': DelimitedList(
            ma_fields.String, delimiter=',', missing=None),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, labels, test):
        """delete data extraction record for a single study by id"""
        # check current user authorization
        extracted_data = db.session.query(DataExtraction).get(id)
        if not extracted_data:
            return no_data_found(
                '<DataExtraction(study_id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=extracted_data.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get extracted data for this study'.format(
                    g.current_user))
        if labels:
            extracted_data.extracted_items = [
                item for item in extracted_data.extracted_items
                if item['label'] not in labels]
        else:
            extracted_data.extracted_items = []
        # in case of "full" deletion, update study's data_extraction_status
        if not extracted_data.extracted_items:
            study = db.session.query(Study).get(id)
            study.data_extraction_status = 'not_started'
        if test is False:
            db.session.commit()
            logger.info('deleted contents of %s', extracted_data)
            return '', 204
        else:
            db.session.rollback()
            return '', 200

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        body=([extracted_item_model], 'data extraction data to be modified'),
        responses={
            200: 'data extraction data was modified (if test = False)',
            401: 'current app user not authorized to modify data extraction',
            404: 'no data extraction with matching id was found',
            }
        )
    @use_args(ExtractedItem(many=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        """modify data extraction record for a single study by id"""
        # check current user authorization
        extracted_data = db.session.query(DataExtraction).get(id)
        review_id = extracted_data.review_id
        if not extracted_data:
            return no_data_found(
                '<DataExtraction(study_id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get extracted data for this study'.format(
                    g.current_user))
        data_extraction_form = db.session.query(ReviewPlan.data_extraction_form)\
            .filter_by(id=review_id).one_or_none()
        if not data_extraction_form:
            return forbidden(
                '<ReviewPlan({})> does not have a data extraction form'.format(review_id))
        labels_map = {item['label']: (item['field_type'],
                                      set(item.get('allowed_values', [])))
                      for item in data_extraction_form[0]}
        # manually validate inputs, given data extraction form specification
        if isinstance(extracted_data.extracted_items, dict):
            extracted_data.extracted_items = []
        extracted_data_map = {
            item['label']: item['value']
            for item in extracted_data.extracted_items}
        for item in args:
            label = item['label']
            value = item['value']
            if label not in labels_map:
                return validation(
                    'label "{}" invalid; available choices are {}'.format(
                        label, list(labels_map.keys())))
            field_type, allowed_values = labels_map[label]
            if field_type == 'bool':
                if value in (1, True, 'true', 't'):
                    validated_value = True
                elif value in (0, False, 'false', 'f'):
                    validated_value = False
                else:
                    return validation(
                        'value "{}" for label "{}" invalid; must be {}'.format(
                            value, label, field_type))
            elif field_type == 'date':
                try:
                    validated_value = str(arrow.get(value).naive)
                except arrow.parser.ParserError:
                    return validation(
                        'value "{}" for label "{}" invalid; must be ISO-formatted {}'.format(
                            value, label, field_type))
            elif field_type in ('int', 'float', 'str'):
                type_ = int if field_type == 'int' \
                    else float if field_type == 'float' \
                    else str
                validated_value = sanitizers.sanitize_type(value, type_)
                if validated_value is None:
                    return validation(
                        'value "{}" for label "{}" invalid; must be {}'.format(
                            value, label, field_type))
            elif field_type == 'select_one':
                if value not in allowed_values:
                    return validation(
                        'value "{}" for label "{}" invalid; must be one of {}'.format(
                            value, label, allowed_values))
                validated_value = value
            elif field_type == 'select_many':
                validated_value = []
                for val in value:
                    if val not in allowed_values:
                        return validation(
                            'value "{}" for label "{}" invalid; must be one of {}'.format(
                                val, label, allowed_values))
                    validated_value.append(val)
            # TODO: implement this country validation
            elif field_type == 'country':
                return forbidden('"country" validation has not yet been implemented -- sorry!')
            else:
                return validation('field_type "{}" is not valid'.format(field_type))
            extracted_data_map[label] = validated_value
        extracted_data.extracted_items = [
            {'label': label, 'value': value}
            for label, value in extracted_data_map.items()]
        # also update study's data_extraction_status
        study = db.session.query(Study).get(id)
        study.data_extraction_status = 'started'
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return DataExtractionSchema().dump(extracted_data).data
