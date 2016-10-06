from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.flaskparser import use_kwargs

from ...lib import constants
from ...lib.parsers import BibTexFile, RisFile
from ...models import db, Citation, Fulltext, Review
from ...tasks import deduplicate_citations
from ..errors import no_data_found, unauthorized, validation
from ..schemas import CitationSchema
from ..authentication import auth


class CitationUploadsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'status': ma_fields.Str(
            missing=None, validate=OneOf(['included', 'excluded'])),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, review_id, status, test):
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
        citation_schema = CitationSchema()
        citations_to_insert = []
        fulltexts_to_insert = []
        for record in citations_file.parse():
            record['review_id'] = review_id
            if status:
                record['status'] = status
                if status == 'included':
                    fulltexts_to_insert.append(
                        Fulltext(record['review_id'], record['citation_id']))
            citation_data = citation_schema.load(record).data
            citations_to_insert.append(Citation(**citation_data))
        if test is False:
            db.session.bulk_save_objects(citations_to_insert)
            if status == 'included':
                db.session.bulk_save_objects(fulltexts_to_insert)
            db.session.commit()
            deduplicate_citations.apply_async(args=[review_id], countdown=60)
