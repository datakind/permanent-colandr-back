import apiflask as af

from .routes import (
    admin,
    auth,
    citation_imports,
    citation_screenings,
    citations,
    health,
    review_plans,
    reviews,
    users,
)


def register_api_blueprints(app: af.APIFlask, url_prefix: str = "/api") -> None:
    app.register_blueprint(admin.bp, url_prefix=_join_ups(url_prefix, admin.bp))
    app.register_blueprint(auth.bp, url_prefix=_join_ups(url_prefix, auth.bp))
    app.register_blueprint(
        citation_imports.bp, url_prefix=_join_ups(url_prefix, citation_imports.bp)
    )
    app.register_blueprint(
        citation_screenings.bp, url_prefix=_join_ups(url_prefix, citation_screenings.bp)
    )
    app.register_blueprint(citations.bp, url_prefix=_join_ups(url_prefix, citations.bp))
    app.register_blueprint(health.bp, url_prefix=_join_ups(url_prefix, health.bp))
    app.register_blueprint(reviews.bp, url_prefix=_join_ups(url_prefix, reviews.bp))
    app.register_blueprint(
        review_plans.bp, url_prefix=_join_ups(url_prefix, review_plans.bp)
    )
    app.register_blueprint(users.bp, url_prefix=_join_ups(url_prefix, users.bp))


def _join_ups(base_url_prefix: str, bp: af.APIBlueprint) -> str:
    return (
        f"{base_url_prefix.rstrip('/')}/{bp.url_prefix.lstrip('/')}"
        if bp.url_prefix is not None
        else base_url_prefix
    )
