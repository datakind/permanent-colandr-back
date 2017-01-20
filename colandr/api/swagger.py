from flask_restplus import fields

# from ..lib import constants
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
     'data_extraction_form': fields.List(fields.Nested(data_extraction_form_item_model)),
     'suggested_keyterms': fields.Nested(review_plan_suggested_keyterms)}
    )
