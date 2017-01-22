from flask_restplus import fields

from ..lib import constants
from colandr import api_


user_model = api_.model(
    'User',
    {'name': fields.String(required=True),
     'email': fields.String(required=True),
     'password': fields.String(required=True)}
    )

data_source_model = api_.model(
    'DataSource',
    {'source_type': fields.String(required=True, enum=['database', 'gray literature']),
     'source_name': fields.String(max_length=100),
     'source_url': fields.String(max_length=500)}
    )

review_model = api_.model(
    'Review',
    {'name': fields.String(required=True, max_length=500),
     'description': fields.String}
    )

review_plan_pico_model = api_.model(
    'ReviewPlanPico',
    {'population': fields.String(max_length=300),
     'intervention': fields.String(max_length=300),
     'comparison': fields.String(max_length=300),
     'outcome': fields.String(max_length=300)}
    )

review_plan_keyterm_model = api_.model(
    'ReviewPlanKeyterm',
    {'label': fields.String(required=True, max_length=25),
     'description': fields.String(max_length=300)}
    )

review_plan_selection_criterion_model = api_.model(
    'ReviewPlanSelectionCriterion',
    {'label': fields.String(required=True, max_length=25),
     'description': fields.String(max_length=300)}
    )

data_extraction_form_item_model = api_.model(
    'DataExtractionFormItem',
    {'label': fields.String(required=True, max_length=25),
     'description': fields.String(max_length=300),
     'field_type': fields.String(required=True, enum=['bool', 'date', 'int', 'float', 'str', 'select_one', 'select_many', 'country']),
     'allowed_values': fields.List(fields.String)}
    )

review_plan_suggested_keyterms = api_.model(
    'ReviewPlanSuggestedKeyterms',
    {'sample_size': fields.Integer(required=True, min=1),
     'incl_keyterms': fields.List(fields.String, required=True),
     'excl_keyterms': fields.List(fields.String, required=True)}
    )

review_plan_model = api_.model(
    'ReviewPlan',
    {'objective': fields.String,
     'research_questions': fields.List(fields.String(max_length=300)),
     'pico': fields.Nested(review_plan_pico_model),
     'keyterms': fields.List(fields.Nested(review_plan_keyterm_model)),
     'selection_criteria': fields.List(fields.Nested(review_plan_selection_criterion_model)),
     'data_extraction_form': fields.List(fields.Nested(data_extraction_form_item_model))}
     # 'suggested_keyterms': fields.Nested(review_plan_suggested_keyterms)}  # not user-set
    )

import_model = api_.model(
    'Import',
    {'review_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'user_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'data_source_id': fields.Integer(required=True, min=1, max=constants.MAX_BIGINT),
     'record_type': fields.String(required=True, enum=['citation', 'fulltext']),
     'num_records': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'status': fields.String(enum=['not_screened', 'included', 'excluded'])}
    )

dedupe_model = api_.model(
    'Dedupe',
    {'review_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'duplicate_of': fields.Integer(min=1, max=constants.MAX_BIGINT),
     'duplicate_score': fields.Float(min=0.0, max=1.0)}
    )

screening_model = api_.model(
    'Screening',
    {'review_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'user_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'citation_id': fields.Integer(min=1, max=constants.MAX_BIGINT),
     'fulltext_id': fields.Integer(min=1, max=constants.MAX_BIGINT),
     'status': fields.String(required=True, enum=['included', 'excluded']),
     'exclude_reasons': fields.List(fields.String(max_length=25))}
    )

citation_model = api_.model(
    'Citation',
    {'review_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'type_of_work': fields.String(max_length=25),
     'title': fields.String(max_length=300),
     'secondary_title': fields.String(max_length=300),
     'abstract': fields.String,
     'pub_year': fields.Integer(min=1, max=constants.MAX_SMALLINT),
     'pub_month': fields.Integer(min=1, max=constants.MAX_SMALLINT),
     'authors': fields.List(fields.String(max_length=100)),
     'keywords': fields.List(fields.String(max_length=100)),
     'type_of_reference': fields.String(max_length=50),
     'journal_name': fields.String(max_length=100),
     'volume': fields.String(max_length=20),
     'issue_number': fields.String(max_length=20),
     'doi': fields.String(max_length=100),
     'issn': fields.String(max_length=20),
     'publisher': fields.String(max_length=100),
     'language': fields.String(max_length=50),
     'other_fields': fields.Raw}
    )

fulltext_model = api_.model(
    'Fulltext',
    {'review_id': fields.Integer(required=True, min=1, max=constants.MAX_INT)}
    )

extracted_item_model = api_.model(
    'ExtractedItem',
    {'label': fields.String(required=True, max_length=25),
     'value': fields.Raw(required=True)}
    )

data_extraction_model = api_.model(
    'DataExtraction',
    {'review_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'extracted_items': fields.List(fields.Nested(extracted_item_model))}
    )

study_model = api_.model(
    'Study',
    {'review_id': fields.Integer(required=True, min=1, max=constants.MAX_INT),
     'data_source_id': fields.Integer(required=True, min=1, max=constants.MAX_BIGINT),
     'tags': fields.List(fields.String(max_length=25))}
    )
