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

from ...models import (db, Citation, Fulltext, DataExtraction, DataSource, Dedupe,
                       FulltextScreening, Import, Review, ReviewPlan, Study)
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
        n_studies_by_source = dict(
            db.session.query(DataSource.source_type, db.func.sum(Import.num_records))
            .filter(Import.data_source_id == DataSource.id)
            .filter(Import.review_id == 1)
            .group_by(DataSource.source_type)
            .all())

        n_unique_studies = db.session.query(Study)\
            .filter(Study.review_id == 1)\
            .filter_by(dedupe_status='not_duplicate')\
            .count()

        n_citations_by_status = dict(
            db.session.query(Study.citation_status, db.func.count(1))
            .filter(Study.review_id == 1)
            .filter(Study.citation_status.in_(['included', 'excluded']))
            .group_by(Study.citation_status)
            .all())
        n_citations_screened = sum(n_citations_by_status.values())
        n_citations_excluded = n_citations_by_status.get('excluded', 0)

        n_fulltexts_by_status = dict(
            db.session.query(Study.fulltext_status, db.func.count(1))
            .filter(Study.review_id == 1)
            .filter(Study.fulltext_status.in_(['included', 'excluded']))
            .group_by(Study.fulltext_status)
            .all())
        n_fulltexts_screened = sum(n_fulltexts_by_status.values())
        n_fulltexts_excluded = n_fulltexts_by_status.get('excluded', 0)

        results = db.session.query(FulltextScreening.exclude_reasons)\
            .filter(FulltextScreening.review_id == 1)\
            .all()
        exclude_reason_counts = dict(collections.Counter(
            itertools.chain.from_iterable(
                [result[0] for result in results if result[0] is not None])))

        n_data_extractions = db.session.query(Study)\
            .filter(Study.review_id == 1)\
            .filter_by(data_extraction_status='complete')\
            .count()

        return {
            'num_studies_by_source': n_studies_by_source,
            'num_unique_studies': n_unique_studies,
            'num_screened_citations': n_citations_screened,
            'num_excluded_citations': n_citations_excluded,
            'num_screened_fulltexts': n_fulltexts_screened,
            'num_excluded_fulltexts': n_fulltexts_excluded,
            'exclude_reason_counts': exclude_reason_counts,
            'num_studies_data_extracted': n_data_extractions
            }


class ReviewExportStudiesResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'extracted_data': ma_fields.Bool(missing=False)
        })
    def get(self, id, extracted_data):
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))

        query = db.session.query(Study)\
            .filter_by(review_id=id)\
            .all()

        query = db.session.query(Fulltext)\
            .filter_by(review_id=id)\
            .options(db.joinedload(Fulltext.citation))
        if extracted_data is True:
            query = query.options(db.joinedload(Fulltext.extracted_data))

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
