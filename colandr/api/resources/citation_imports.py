from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow import ValidationError
from marshmallow.validate import OneOf, Range
from webargs.flaskparser import use_kwargs

from ...lib import constants
from ...lib.parsers import BibTexFile, RisFile
from ...models import db, Citation, Fulltext, Import, Review
from ...tasks import deduplicate_citations
from ..errors import no_data_found, unauthorized, validation
from ..schemas import CitationSchema, DataSourceSchema, ImportSchema
from ..authentication import auth


class CitationsImportsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT))
        })
    def get(self, review_id):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to add citations to this review'.format(g.current_user))
        results = review.imports.filter_by(record_type='citation')
        return ImportSchema(many=True).dump(results.all()).data

    @swagger.operation()
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'source_type': ma_fields.Str(
            missing=None, validate=OneOf(['database', 'gray literature'])),
        'source_reference': ma_fields.Str(
            missing=None),
        'status': ma_fields.Str(
            missing=None, validate=OneOf(['not_screened', 'included', 'excluded'])),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, review_id,
             source_type, source_reference, status, test):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to add citations to this review'.format(g.current_user))
        fname = uploaded_file.filename
        if fname.endswith('.bib'):
            citations_file = BibTexFile(uploaded_file.stream)
        elif fname.endswith('.ris') or fname.endswith('.txt'):
            citations_file = RisFile(uploaded_file.stream)
        else:
            return validation('unknown file type: "{}"'.format(fname))
        data_source = None
        if source_type is not None or source_reference is not None:
            data_source = {
                'source_type': source_type,
                'source_reference': source_reference or ''}
            try:
                DataSourceSchema().validate(data_source)
            except ValidationError as e:
                return validation(e.messages)
        citation_schema = CitationSchema()
        citations_to_insert = []
        fulltexts_to_insert = []
        for record in citations_file.parse():
            record['review_id'] = review_id
            if data_source:
                record['data_source'] = data_source
            if status:
                record['status'] = status
                if status == 'included':
                    fulltexts_to_insert.append(
                        Fulltext(record['review_id'], record['citation_id']))
            citation_data = citation_schema.load(record).data
            citations_to_insert.append(Citation(**citation_data))
        # don't forget about a record of the import
        citations_import = Import(
            review_id, g.current_user.id, 'citation', len(citations_to_insert),
            status=status, data_source=data_source)
        if test is False:
            db.session.bulk_save_objects(citations_to_insert)
            db.session.add(citations_import)
            if status == 'included':
                db.session.bulk_save_objects(fulltexts_to_insert)
            db.session.commit()
            deduplicate_citations.apply_async(args=[review_id], countdown=60)
