import collections
import csv
import io
import itertools

from flask import g, make_response
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ...lib import constants
from ...models import (db, DataSource,
                       FulltextScreening, Import, Review, ReviewPlan, Study)
from ..errors import no_data_found, unauthorized
from ..authentication import auth
from colandr import api_

ns = api_.namespace(
    'review_exports', path='/reviews/<int:id>/export',
    description='export review prisma or studies data')


@ns.route('/prisma')
@ns.doc(
    summary='export numbers needed to make a review PRISMA diagram',
    produces=['application/json'],
    )
class ReviewExportPrismaResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        responses={200: 'successfully got review prisma data',
                   401: 'current app user not authorized to export review prisma data',
                   404: 'no review with matching id was found',
                   }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT))
        })
    def get(self, id):
        """export numbers needed to make a review PRISMA diagram"""
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                review.users.filter_by(id=g.current_user.id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))
        # get counts by step, i.e. prisma
        n_studies_by_source = dict(
            db.session.query(DataSource.source_type, db.func.sum(Import.num_records))
            .filter(Import.data_source_id == DataSource.id)
            .filter(Import.review_id == id)
            .group_by(DataSource.source_type)
            .all())

        n_unique_studies = db.session.query(Study)\
            .filter(Study.review_id == id)\
            .filter_by(dedupe_status='not_duplicate')\
            .count()

        n_citations_by_status = dict(
            db.session.query(Study.citation_status, db.func.count(1))
            .filter(Study.review_id == id)
            .filter(Study.citation_status.in_(['included', 'excluded']))
            .group_by(Study.citation_status)
            .all())
        n_citations_screened = sum(n_citations_by_status.values())
        n_citations_excluded = n_citations_by_status.get('excluded', 0)

        n_fulltexts_by_status = dict(
            db.session.query(Study.fulltext_status, db.func.count(1))
            .filter(Study.review_id == id)
            .filter(Study.fulltext_status.in_(['included', 'excluded']))
            .group_by(Study.fulltext_status)
            .all())
        n_fulltexts_screened = sum(n_fulltexts_by_status.values())
        n_fulltexts_excluded = n_fulltexts_by_status.get('excluded', 0)

        results = db.session.query(FulltextScreening.exclude_reasons)\
            .filter(FulltextScreening.review_id == id)\
            .all()
        exclude_reason_counts = dict(collections.Counter(
            itertools.chain.from_iterable(
                [result[0] for result in results if result[0] is not None])))

        n_data_extractions = db.session.query(Study)\
            .filter(Study.review_id == id)\
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


@ns.route('/studies')
@ns.doc(
    summary='export a CSV of studies metadata and extracted data',
    produces=['text/csv'],
    )
class ReviewExportStudiesResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        description='NOTE: Calling this endpoint via Swagger could cause it to crash on account of #BigData',
        responses={200: 'successfully got review studies data',
                   401: 'current app user not authorized to export review studies data',
                   404: 'no review with matching id was found',
                   }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        })
    def get(self, id):
        """export a CSV of studies metadata and extracted data"""
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                review.users.filter_by(id=g.current_user.id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))

        query = db.session.query(Study)\
            .filter_by(review_id=id)\
            .order_by(Study.id)

        fieldnames = [
            'study_id',
            'deduplication_status',
            'citation_screening_status',
            'fulltext_screening_status',
            'data_extraction_screening_status',
            'data_source_type',
            'data_source_name',
            'data_source_url',
            'citation_title',
            'citation_abstract',
            'citation_authors',
            'citation_journal_name',
            'citation_journal_volume',
            'citation_pub_year',
            'citation_keywords',
            'fulltext_filename',
            'fulltext_exclude_reasons'
            ]

        data_extraction_form = db.session.query(ReviewPlan.data_extraction_form)\
            .filter_by(id=id).one_or_none()
        if data_extraction_form:
            extraction_labels = [item['label'] for item in data_extraction_form[0]]
            extraction_types = [item['field_type'] for item in data_extraction_form[0]]
            fieldnames.extend(extraction_labels)

        rows = []
        for study in query:
            row = [
                study.id,
                study.dedupe_status,
                study.citation_status,
                study.fulltext_status,
                study.data_extraction_status,
                study.data_source.source_type,
                study.data_source.source_name,
                study.data_source.source_url,
                study.citation.title,
                study.citation.abstract,
                '; '.join(study.citation.authors) if study.citation.authors else None,
                study.citation.journal_name,
                study.citation.volume,
                study.citation.pub_year,
                '; '.join(study.citation.keywords) if study.citation.keywords else None,
                ]
            if study.fulltext:
                row.extend(
                    [study.fulltext.original_filename,
                     '; '.join(study.fulltext.exclude_reasons) if study.fulltext.exclude_reasons else None]
                    )
            else:
                row.extend([None, None])
            if data_extraction_form:
                if study.data_extraction:
                    extracted_data = {
                        item['label']: item['value']
                        for item in study.data_extraction.extracted_items}
                    row.extend(
                        '; '.join(extracted_data.get(label, [])) if type_ in ('select_one', 'select_many')
                        else extracted_data.get(label, None)
                        for label, type_ in zip(extraction_labels, extraction_types)
                        )
                else:
                    row.extend(None for _ in range(len(extraction_labels)))
            rows.append(row)

        f = io.StringIO()
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(fieldnames)
        writer.writerows(rows)
        response = make_response(f.getvalue(), 200)
        response.headers['Content-type'] = 'text/csv'
        return response
