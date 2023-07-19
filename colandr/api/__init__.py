import flask_praetorian
from flask_restx import Api

from .auth import ns as ns_auth
from .errors import ns as errors_ns
from .health import ns as ns_health
from .resources.citation_imports import ns as citation_imports_ns
from .resources.citation_screenings import ns as citation_screenings_ns
from .resources.citations import ns as citations_ns
from .resources.data_extractions import ns as data_extractions_ns
from .resources.fulltext_screenings import ns as fulltext_screenings_ns
from .resources.fulltext_uploads import ns as fulltext_uploads_ns
from .resources.fulltexts import ns as fulltexts_ns
from .resources.review_exports import ns as review_exports_ns
from .resources.review_plans import ns as review_plans_ns
from .resources.review_progress import ns as review_progress_ns
from .resources.review_teams import ns as review_teams_ns
from .resources.reviews import ns as reviews_ns
from .resources.studies import ns as studies_ns
from .resources.study_tags import ns as study_tags_ns
from .resources.users import ns as users_ns
from .swagger import ns as swagger_ns


api_ = Api(
    version="1.0",
    prefix="/api",
    doc="/docs",
    default_mediatype="application/json",
    title="colandr",
    description="REST API powering the colandr app",
    authorizations={
        "access_token": {"type": "apiKey", "in": "header", "name": "Authorization"}
        # NOTE: below style is for OpenAPI v3, which flask-restx doesn't yet support :/
        # "access_token": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    },
)

# this is a built-in hack!
flask_praetorian.PraetorianError.register_error_handler_with_flask_restx(api_)

api_.add_namespace(ns_auth)
api_.add_namespace(errors_ns)
api_.add_namespace(ns_health)
api_.add_namespace(swagger_ns)
api_.add_namespace(users_ns)
api_.add_namespace(reviews_ns)
api_.add_namespace(review_teams_ns)
api_.add_namespace(review_progress_ns)
api_.add_namespace(review_exports_ns)
api_.add_namespace(review_plans_ns)
api_.add_namespace(studies_ns)
api_.add_namespace(study_tags_ns)
api_.add_namespace(citations_ns)
api_.add_namespace(citation_imports_ns)
api_.add_namespace(citation_screenings_ns)
api_.add_namespace(fulltexts_ns)
api_.add_namespace(fulltext_uploads_ns)
api_.add_namespace(fulltext_screenings_ns)
api_.add_namespace(data_extractions_ns)
