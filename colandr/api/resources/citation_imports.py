from flask import g, current_app
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow import ValidationError
from marshmallow.validate import Length, OneOf, Range, URL
from webargs.flaskparser import use_kwargs

from sqlalchemy import create_engine

from colandr import api_
from ...lib import constants
from ...lib.parsers import BibTexFile, RisFile
from ...models import db, Citation, DataSource, Fulltext, Import, Review, Study
from ...tasks import deduplicate_citations, get_citations_text_content_vectors
from ..errors import not_found_error, forbidden_error, validation_error
from ..schemas import CitationSchema, DataSourceSchema, ImportSchema
from ..authentication import auth


ns = api_.namespace(
    'citation_imports', path='/citations/imports',
    description='import citations in bulk and get import history')


@ns.route('')
@ns.doc(
    summary='import citations in bulk and get import history',
    produces=['application/json'],
    )
class CitationsImportsResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        params={
            'review_id': {'in': 'query', 'type': 'integer', 'required': True,
                          'description': 'unique identifier of review for which citations were imported'},
            },
        responses={
            200: 'successfully got citation import history',
            403: 'current app user forbidden to get citation import history',
            404: 'no review with matching id was found',
            }
        )
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT))
        })
    def get(self, review_id):
        """get citation import history for a review"""
        review = db.session.query(Review).get(review_id)
        if not review:
            return not_found_error('<Review(id={})> not found'.format(review_id))
        if (g.current_user.is_admin is False and
                g.current_user.reviews.filter_by(id=review_id).one_or_none() is None):
            return forbidden_error(
                '{} forbidden to add citations to this review'.format(g.current_user))
        results = review.imports.filter_by(record_type='citation')
        return ImportSchema(many=True).dump(results.all()).data

    @ns.doc(
        params={
            'uploaded_file': {'in': 'formData', 'type': 'file', 'required': True,
                              'description': 'file containing one or many citations in a standard format (.ris or .bib)'},
            'review_id': {'in': 'query', 'type': 'integer', 'required': True,
                          'description': 'unique identifier for review for which citations will be imported'},
            'source_type': {'in': 'query', 'type': 'string',
                            'enum': ['database', 'gray literature'],
                            'description': 'type of source through which citations were found'},
            'source_name': {'in': 'query', 'type': 'string',
                            'description': 'name of source through which citations were found'},
            'source_url': {'in': 'query', 'type': 'string', 'format': 'url',
                           'description': 'url of source through which citations were found'},
            'status': {'in': 'query', 'type': 'string',
                       'enum': ['not_screened', 'included', 'excluded'],
                       'description': 'known screening status of citations, if anything'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'successfully imported citations in bulk',
            403: 'current app user forbidden to import citations for this review',
            404: 'no review with matching id was found'
            }
        )
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'source_type': ma_fields.Str(
            required=True, validate=OneOf(['database', 'gray literature'])),
        'source_name': ma_fields.Str(
            missing=None, validate=Length(max=100)),
        'source_url': ma_fields.Str(
            missing=None, validate=[URL(relative=False), Length(max=500)]),
        'status': ma_fields.Str(
            missing=None, validate=OneOf(['not_screened', 'included', 'excluded'])),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, review_id,
             source_type, source_name, source_url, status, test):
        """import citations in bulk for a review"""
        review = db.session.query(Review).get(review_id)
        if not review:
            return not_found_error('<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return forbidden_error(
                '{} forbidden to add citations to this review'.format(g.current_user))
        fname = uploaded_file.filename
        if fname.endswith('.bib'):
            try:
                citations_file = BibTexFile(uploaded_file.stream)
            except Exception:
                return validation_error(
                    'unable to parse BibTex citations file: "{}"'.format(fname))
        elif fname.endswith('.ris') or fname.endswith('.txt'):
            try:
                citations_file = RisFile(uploaded_file.stream)
            except Exception:
                return validation_error(
                    'unable to parse RIS citations file: "{}"'.format(fname))
        else:
            return validation_error('unknown file type: "{}"'.format(fname))

        # upsert the data source
        try:
            DataSourceSchema().validate(
                {'source_type': source_type,
                 'source_name': source_name,
                 'source_url': source_url})
        except ValidationError as e:
            return validation_error(e.messages)
        data_source = db.session.query(DataSource)\
            .filter_by(source_type=source_type, source_name=source_name).one_or_none()
        if data_source is None:
            data_source = DataSource(source_type, source_name, source_url=source_url)
            db.session.add(data_source)
        if test is False:
            db.session.commit()
            current_app.logger.info('inserted %s', data_source)
            data_source_id = data_source.id
        else:
            data_source_id = 0

        # TODO: make this an async task?
        engine = create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
        # parse and iterate over imported citations
        # create lists of study and citation dicts to insert
        citation_schema = CitationSchema()
        citations_to_insert = []
        # rather than doing it in a for loop, we've switched to a while loop
        # so that parsing errors on individual citations can be caught and logged
        # for record in citations_file.parse():
        #     record['review_id'] = review_id
        #     citations_to_insert.append(citation_schema.load(record).data)
        records = citations_file.parse()
        while True:
            try:
                record = next(records)
                record['review_id'] = review_id
                citations_to_insert.append(citation_schema.load(record).data)
            except StopIteration:
                break
            except Exception as e:
                current_app.logger.warning('parsing error: %s', e)
        n_citations = len(citations_to_insert)

        user_id = g.current_user.id
        if status is None:
            studies_to_insert = [
                {'user_id': user_id,
                 'review_id': review_id,
                 'data_source_id': data_source_id}
                for i in range(n_citations)]
        else:
            studies_to_insert = [
                {'user_id': user_id,
                 'review_id': review_id,
                 'data_source_id': data_source_id,
                 'citation_status': status}
                for i in range(n_citations)]

        if test is True:
            db.session.rollback()
            return

        # insert studies, and get their primary keys _back_
        stmt = db.insert(Study).values(studies_to_insert).returning(Study.id)
        with engine.connect() as conn:
            study_ids = [result[0] for result in conn.execute(stmt)]

        # add study ids to citations as their primary keys
        # then bulk insert as mappings
        # this method is required because not all citations have all fields
        for study_id, citation in zip(study_ids, citations_to_insert):
            citation['id'] = study_id
        db.session.bulk_insert_mappings(Citation, citations_to_insert)

        # if citations' status is "included", we have to bulk insert
        # the corresponding fulltexts, since bulk operations won't trigger
        # the fancy events defined in models.py
        if status == 'included':
            with engine.connect() as conn:
                conn.execute(
                    Fulltext.__table__.insert(),
                    [{'id': study_id, 'review_id': review_id}
                     for study_id in study_ids]
                    )

        # don't forget about a record of the import
        citations_import = Import(
            review_id, user_id, data_source_id, 'citation', n_citations,
            status=status)
        db.session.add(citations_import)
        db.session.commit()
        current_app.logger.info(
            'imported %s citations from file "%s" into %s',
            n_citations, fname, review)

        # lastly, don't forget to deduplicate the citations and get their word2vecs
        deduplicate_citations.apply_async(args=[review_id], countdown=60)
        get_citations_text_content_vectors.apply_async(
            args=[review_id], countdown=60)
