from flask import g, current_app
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow import ValidationError
from marshmallow.validate import Length, OneOf, Range, URL
from webargs.flaskparser import use_kwargs

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from ...lib import constants
from ...lib.parsers import BibTexFile, RisFile
from ...models import db, Citation, DataSource, Fulltext, Import, Review, Study
from ...tasks import deduplicate_citations
from ..errors import no_data_found, unauthorized, validation
from ..schemas import CitationSchema, DataSourceSchema, ImportSchema, StudySchema
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

        if test is True:
            return ''

        # upsert the data source
        data_source = {
            'source_type': source_type,
            'source_name': source_name,
            'source_url': source_url}
        try:
            DataSourceSchema().validate(data_source)
        except ValidationError as e:
            return validation(e.messages)
        # let's try an upsert
        # TODO: just switch the order, i.e. query for an id, and if not found,
        # then insert it normally; it's more clear
        engine = create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
        stmt = insert(DataSource)\
            .values(source_type=source_type, source_name=source_name, source_url=source_url)\
            .on_conflict_do_nothing(
                index_elements=[DataSource.source_type, DataSource.source_name])
        with engine.connect() as conn:
            result = conn.execute(stmt)
            data_source_id = result.inserted_primary_key
        # result = db.session.connection().execute(stmt)
        # data_source_id = result.inserted_primary_key
        # this type-name pair was new and inserted; since the primary key
        # is only one column, take the first element of the returned list
        if data_source_id is not None:
            data_source_id = data_source_id[0]
        # this type-name pair already exists; for some reason, sqlalchemy
        # absolutely WILL NOT return it, so we have to query for it ourselves
        else:
            data_source_id = db.session.query(DataSource.id)\
                .filter_by(source_type=source_type).filter_by(source_name=source_name)\
                .scalar()

        # parse and iterate over imported citations
        # create lists of study and citation dicts to insert
        user_id = g.current_user.id
        studies_to_insert = []
        citations_to_insert = []
        citation_schema = CitationSchema()
        for record in citations_file.parse():
            studies_to_insert.append(
                {'user_id': user_id,
                 'review_id': review_id,
                 'data_source_id': data_source_id})
            record['review_id'] = review_id
            if status:
                record['status'] = status
            citations_to_insert.append(citation_schema.load(record).data)

        # insert studies, and get their primary keys _back_
        stmt = db.insert(Study).values(studies_to_insert)\
            .returning(Study.id)
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
            review_id, user_id, data_source_id, 'citation', len(study_ids),
            status=status)
        db.session.add(citations_import)

        db.session.commit()

        # TODO: fix this
        # deduplicate_citations.apply_async(args=[review_id], countdown=60)
