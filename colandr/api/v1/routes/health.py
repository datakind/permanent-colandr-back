import apiflask as af
import celery
import redis.client
import redis.exceptions
import sqlalchemy as sa
import sqlalchemy.exc
from flask.views import MethodView

from ....extensions import db


bp = af.APIBlueprint("health", __name__, url_prefix="/health")


class HealthAPI(MethodView):
    @bp.doc(
        summary="check health of API",
        responses={
            200: "API is healthy",
            404: "API is unavailable",
            500: "API is unhealthy",
        },
    )
    @bp.output({"message": af.fields.String()})
    def get(self):
        redis_conn = celery.current_app.backend.client  # type: ignore
        assert isinstance(redis_conn, redis.client.Redis)  # type guard
        try:
            _ = redis_conn.ping()
        except redis.exceptions.ConnectionError:
            af.abort(500, message="message broker is unavailable")
        try:
            _ = db.session.execute(sa.text("SELECT 1")).scalar()
        except sqlalchemy.exc.OperationalError:
            af.abort(500, message="database is unavailable")

        return {"message": "OK"}


bp.add_url_rule("/", view_func=HealthAPI.as_view("health"))
