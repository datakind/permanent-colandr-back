import collections
import csv
import io
import itertools

from flask import g, make_response
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.flaskparser import use_kwargs

from ...models import (db, Citation, Fulltext, DataExtraction,
                       FulltextScreening, Review, ReviewPlan)
from ...lib import constants
from ..errors import no_data_found, unauthorized
from ..authentication import auth


class ReviewExportPrismaResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT))
        })
    def get(self, id):
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))
        # get counts by step, i.e. prisma
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

        n_studies_data_extracted = db.session.query(DataExtraction)\
            .filter_by(review_id=id)\
            .filter(DataExtraction.extracted_items != {})\
            .count()

        return {
            'n_all_citations': n_all_citations,
            'n_unique_citations': n_unique_citations,
            'n_screened_citations': n_screened_citations,
            'n_excluded_citations': n_excluded_citations,
            'n_screened_fulltexts': n_screened_fulltexts,
            'n_excluded_fulltexts': n_excluded_fulltexts,
            'exclude_reason_counts': exclude_reason_counts,
            'n_studies_data_extracted': n_studies_data_extracted
            }


class ReviewExportRefsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'status': ma_fields.Str(
            missing=None, validate=OneOf(['included', 'excluded'])),
        'extracted_data': ma_fields.Bool(missing=False)
        })
    def get(self, id, status, extracted_data):
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))
        query = db.session.query(Fulltext)\
            .filter_by(review_id=id)\
            .options(db.joinedload(Fulltext.citation))
        if extracted_data is True:
            query = query.options(db.joinedload(Fulltext.extracted_data))
        if status is not None:
            query = query.filter(Fulltext.status == status)

        fieldnames = ['title', 'authors', 'journal_name', 'journal_volume', 'pub_year',
                      'status', 'exclude_reasons']
        rows = []
        if extracted_data is False:
            rows.append(fieldnames)
            for result in query:
                rows.append([result.citation.title,
                             '; '.join(result.citation.authors),
                             result.citation.journal_name,
                             result.citation.volume,
                             result.citation.pub_year,
                             result.status,
                             '; '.join(result.exclude_reasons)
                             ])
        else:
            rows.append(fieldnames)
            data_extraction_form = db.session.query(ReviewPlan.data_extraction_form)\
                .filter(ReviewPlan.review_id == id).one_or_none()
            if not data_extraction_form:
                raise Exception
            extraction_labels = sorted(item['label'] for item in data_extraction_form[0])
            fieldnames.extend(extraction_labels)
            for result in query:
                row = [result.citation.title,
                       '; '.join(result.citation.authors),
                       result.citation.journal_name,
                       result.citation.volume,
                       result.citation.pub_year,
                       result.status,
                       '; '.join(result.exclude_reasons)
                       ]
                try:
                    extracted_data = {item['label']: item['value']
                                      for item in result.extracted_data.extracted_data}
                except (AttributeError, TypeError):
                    row.extend(None for _ in range(len(extraction_labels)))
                    rows.append(row)
                    continue
                for label in extraction_labels:
                    value = extracted_data.get(label)
                    if isinstance(value, list):
                        row.append('; '.join(value))
                    else:
                        row.append(value)
                rows.append(row)

        f = io.StringIO()
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerows(rows)
        resp = make_response(f.getvalue(), 200)
        resp.headers['Content-type'] = 'text/csv'
        return resp
