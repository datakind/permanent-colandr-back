import flask_praetorian
from flask_restx import Api

from .auth import ns as ns_auth
from .errors import ns as ns_errors
from .health import ns as ns_health
from .resources.citation_imports import ns as ns_citation_imports
from .resources.citation_screenings import ns as ns_citation_screenings
from .resources.citations import ns as ns_citations
from .resources.data_extractions import ns as ns_data_extractions
from .resources.deduplicate_studies import ns as ns_deduplicate_studies
from .resources.fulltext_screenings import ns as ns_fulltext_screenings
from .resources.fulltext_uploads import ns as ns_fulltext_uploads
from .resources.fulltexts import ns as ns_fulltexts
from .resources.review_exports import ns as ns_review_exports
from .resources.review_plans import ns as ns_review_plans
from .resources.review_progress import ns as ns_review_progress
from .resources.review_teams import ns as ns_review_teams
from .resources.reviews import ns as ns_reviews
from .resources.studies import ns as ns_studies
from .resources.study_tags import ns as ns_study_tags
from .resources.users import ns as ns_users
from .swagger import ns as ns_swagger


api_v1 = Api(
    version="1.0",
    prefix="/api",  # NOTE: not using "/api/v1" here to maintain backwards compatibility
    doc="/docs",
    default_mediatype="application/json",
    title="colandr",
    description="REST API powering the colandr app",
    authorizations={
        "api_key": {"type": "apiKey", "in": "header", "name": "Authorization"}
        # NOTE: below style is for OpenAPI v3, which flask-restx doesn't yet support :/
        # "access_token": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    },
    security="api_key",
)

# this is a built-in hack!
flask_praetorian.PraetorianError.register_error_handler_with_flask_restx(api_v1)

api_v1.add_namespace(ns_auth)
api_v1.add_namespace(ns_errors)
api_v1.add_namespace(ns_health)
api_v1.add_namespace(ns_swagger)
api_v1.add_namespace(ns_users)
api_v1.add_namespace(ns_reviews)
api_v1.add_namespace(ns_review_teams)
api_v1.add_namespace(ns_review_progress)
api_v1.add_namespace(ns_review_exports)
api_v1.add_namespace(ns_review_plans)
api_v1.add_namespace(ns_studies)
api_v1.add_namespace(ns_study_tags)
api_v1.add_namespace(ns_citations)
api_v1.add_namespace(ns_citation_imports)
api_v1.add_namespace(ns_citation_screenings)
api_v1.add_namespace(ns_deduplicate_studies)
api_v1.add_namespace(ns_fulltexts)
api_v1.add_namespace(ns_fulltext_uploads)
api_v1.add_namespace(ns_fulltext_screenings)
api_v1.add_namespace(ns_data_extractions)
