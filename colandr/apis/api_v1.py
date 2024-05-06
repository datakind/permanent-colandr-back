# ruff: noqa: E402
from flask_restx import Api


api = Api(
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


api.add_namespace(auth.ns)
api.add_namespace(health.ns)
api.add_namespace(swagger.ns)
api.add_namespace(users.ns)
api.add_namespace(reviews.ns)
api.add_namespace(review_teams.ns)
api.add_namespace(review_progress.ns)
api.add_namespace(review_exports.ns)
api.add_namespace(review_plans.ns)
api.add_namespace(studies.ns)
api.add_namespace(study_tags.ns)
api.add_namespace(citations.ns)
api.add_namespace(citation_imports.ns)
api.add_namespace(citation_screenings.ns)
api.add_namespace(deduplicate_studies.ns)
api.add_namespace(fulltexts.ns)
api.add_namespace(fulltext_uploads.ns)
api.add_namespace(fulltext_screenings.ns)
api.add_namespace(data_extractions.ns)
api.add_namespace(exports.ns)
