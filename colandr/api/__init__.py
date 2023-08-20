import flask_praetorian
from flask_restx import Api

from .auth import ns as ns_auth
from .errors import ns as ns_errors
from .health import ns as ns_health
from .resources.citation_imports import ns as ns_citation_imports
from .resources.citation_screenings import ns as ns_citation_screenings
from .resources.citations import ns as ns_citations
from .resources.data_extractions import ns as ns_data_extractions
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


api_ = Api(
    version="1.0",
    prefix="/api",
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
flask_praetorian.PraetorianError.register_error_handler_with_flask_restx(api_)

api_.add_namespace(ns_auth)
api_.add_namespace(ns_errors)
api_.add_namespace(ns_health)
api_.add_namespace(ns_swagger)
api_.add_namespace(ns_users)
api_.add_namespace(ns_reviews)
api_.add_namespace(ns_review_teams)
api_.add_namespace(ns_review_progress)
api_.add_namespace(ns_review_exports)
api_.add_namespace(ns_review_plans)
api_.add_namespace(ns_studies)
api_.add_namespace(ns_study_tags)
api_.add_namespace(ns_citations)
api_.add_namespace(ns_citation_imports)
api_.add_namespace(ns_citation_screenings)
api_.add_namespace(ns_fulltexts)
api_.add_namespace(ns_fulltext_uploads)
api_.add_namespace(ns_fulltext_screenings)
api_.add_namespace(ns_data_extractions)
