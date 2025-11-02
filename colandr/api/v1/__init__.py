import apiflask as af

from .routes import health


def register_api_blueprints(app: af.APIFlask, url_prefix: str = "/api") -> None:
    app.register_blueprint(health.bp, url_prefix=_join_ups(url_prefix, health.bp))


def _join_ups(base_url_prefix: str, bp: af.APIBlueprint) -> str:
    return (
        f"{base_url_prefix.rstrip('/')}/{bp.url_prefix.lstrip('/')}"
        if bp.url_prefix is not None
        else base_url_prefix
    )
