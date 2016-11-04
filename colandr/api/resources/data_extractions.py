import arrow

from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants, sanitizers
from ...models import db, DataExtraction, ReviewPlan
from ..errors import forbidden, no_data_found, unauthorized, validation
from ..schemas import ExtractedItem, DataExtractionSchema
from ..authentication import auth


class DataExtractionResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        })
    def get(self, id):
        # check current user authorization
        extracted_data = db.session.query(DataExtraction)\
            .filter_by(fulltext_id=id).one_or_none()
        if not extracted_data:
            return no_data_found(
                '<DataExtraction(fulltext_id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                g.current_user.reviews.filter_by(id=extracted_data.review_id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get extracted data for this fulltext'.format(
                    g.current_user))
        return DataExtractionSchema().dump(extracted_data).data

    # NOTE: since extracted data are created automatically upon fulltext inclusion
    # and deleted automatically upon fulltext exclusion, "delete" here amounts
    # to nulling out some or all of its non-required fields
    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'labels': DelimitedList(
            ma_fields.String, delimiter=',', missing=None),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, labels, test):
        # check current user authorization
        extracted_data = db.session.query(DataExtraction)\
            .filter_by(fulltext_id=id).one_or_none()
        if not extracted_data:
            return no_data_found(
                '<DataExtraction(fulltext_id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=extracted_data.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get extracted data for this fulltext'.format(
                    g.current_user))
        if labels:
            extracted_data.extracted_data = [
                item for item in extracted_data.extracted_data
                if item['label'] not in labels]
        else:
            extracted_data.extracted_data = []
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return '', 204

    @swagger.operation()
    @use_args(ExtractedItem(many=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        # check current user authorization
        extracted_data = db.session.query(DataExtraction)\
            .filter_by(fulltext_id=id).one_or_none()
        if not extracted_data:
            return no_data_found(
                '<DataExtraction(fulltext_id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=extracted_data.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get extracted data for this fulltext'.format(
                    g.current_user))
        data_extraction_form = db.session.query(ReviewPlan.data_extraction_form)\
            .filter_by(review_id=extracted_data.review_id).one_or_none()
        if not data_extraction_form:
            return forbidden(
                '<ReviewPlan({})> does not have a data extraction form'.format(
                    extracted_data.review_id))
        labels_map = {item['label']: (item['field_type'],
                                      set(item.get('allowed_values', [])))
                      for item in data_extraction_form[0]}
        # manually validate inputs, given data extraction form specification
        if isinstance(extracted_data.extracted_data, dict):
            extracted_data.extracted_data = []
        extracted_data_map = {
            item['label']: item['value']
            for item in extracted_data.extracted_data}
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
                    validated_value = arrow.get(value).naive
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
                raise NotImplementedError('burton apologizes for this inconvenience')
            else:
                return validation('field_type "{}" is not valid'.format(field_type))
            extracted_data_map[label] = validated_value
        extracted_data.extracted_data = [
            {'label': label, 'value': value}
            for label, value in extracted_data_map.items()]
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return DataExtractionSchema().dump(extracted_data).data
