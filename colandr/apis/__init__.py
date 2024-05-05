# ruff: noqa: E402
from flask_restx import Api


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


api_v2 = Api(
    version="2.0",
    prefix="/api/v2",
    doc="/docs/v2",
    default_mediatype="application/json",
    title="colandr",
    description="REST API (v2) powering the colandr app",
    authorizations={
        "api_key": {"type": "apiKey", "in": "header", "name": "Authorization"}
        # NOTE: below style is for OpenAPI v3, which flask-restx doesn't yet support :/
        # "access_token": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    },
    security="api_key",
)

from . import auth, health, swagger
from .resources import (
    citation_imports,
    citation_screenings,
    citations,
    data_extractions,
    deduplicate_studies,
    exports,
    fulltext_screenings,
    fulltext_uploads,
    fulltexts,
    review_exports,
    review_plans,
    review_progress,
    review_teams,
    reviews,
    studies,
    study_tags,
    users,
)


api_v1.add_namespace(auth.ns)
api_v1.add_namespace(health.ns)
api_v1.add_namespace(swagger.ns)
api_v1.add_namespace(users.ns)
api_v1.add_namespace(reviews.ns)
api_v1.add_namespace(review_teams.ns)
api_v1.add_namespace(review_progress.ns)
api_v1.add_namespace(review_exports.ns)
api_v1.add_namespace(review_plans.ns)
api_v1.add_namespace(studies.ns)
api_v1.add_namespace(study_tags.ns)
api_v1.add_namespace(citations.ns)
api_v1.add_namespace(citation_imports.ns)
api_v1.add_namespace(citation_screenings.ns)
api_v1.add_namespace(deduplicate_studies.ns)
api_v1.add_namespace(fulltexts.ns)
api_v1.add_namespace(fulltext_uploads.ns)
api_v1.add_namespace(fulltext_screenings.ns)
api_v1.add_namespace(data_extractions.ns)
api_v1.add_namespace(exports.ns)
