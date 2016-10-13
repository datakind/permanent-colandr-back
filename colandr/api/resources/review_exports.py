import collections
import itertools

from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ...models import (db, Citation, Fulltext, FulltextExtractedData,
                       FulltextScreening, Review)
from ...lib import constants
from ..errors import no_data_found, unauthorized
from ..authentication import auth


class ReviewExportResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'prisma': ma_fields.Bool(missing=False)
        })
    def get(self, id, prisma):
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))
        export = {}
        # export prisma counts
        if prisma is True:
            n_citations_by_status = dict(
                db.session.query(Citation.status, db.func.count(1))
                .filter_by(review_id=id)
                .group_by(Citation.status)
                .all())
            n_dupe_citations = db.session.query(Citation)\
                .filter_by(review_id=id)\
                .filter(Citation.deduplication['is_duplicate'].astext == 'true')\
                .count()
            n_all_citations = sum(n_citations_by_status.values())
            n_unique_citations = n_all_citations - n_dupe_citations
            n_screened_citations = n_citations_by_status['included'] + n_citations_by_status['excluded']
            n_excluded_citations = n_citations_by_status['excluded']

            n_incl_excl_fulltexts = dict(
                db.session.query(Fulltext.status, db.func.count(1))
                .filter_by(review_id=id)
                .filter(Fulltext.status.in_(['included', 'excluded']))
                .group_by(Fulltext.status)
                .all())
            n_screened_fulltexts = sum(n_incl_excl_fulltexts.values())
            n_excluded_fulltexts = n_incl_excl_fulltexts['excluded']

            results = db.session.query(Fulltext.id, FulltextScreening.exclude_reasons)\
                .filter(Fulltext.id == FulltextScreening.fulltext_id)\
                .filter(Fulltext.review_id == id)\
                .filter(Fulltext.status == 'excluded')\
                .all()
            exclude_reason_counts = dict(collections.Counter(
                itertools.chain.from_iterable(result[1] for result in results)))

            n_studies_data_extracted = db.session.query(FulltextExtractedData)\
                .filter_by(review_id=id)\
                .filter(FulltextExtractedData.extracted_data != {})\
                .count()

            export['prisma'] = {
                'n_all_citations': n_all_citations,
                'n_unique_citations': n_unique_citations,
                'n_screened_citations': n_screened_citations,
                'n_excluded_citations': n_excluded_citations,
                'n_screened_fulltexts': n_screened_fulltexts,
                'n_excluded_fulltexts': n_excluded_fulltexts,
                'exclude_reason_counts': exclude_reason_counts,
                'n_studies_data_extracted': n_studies_data_extracted
                }
        return export
