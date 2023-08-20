import redis
import sqlalchemy as sa
from celery import current_app as current_celery_app
from flask_restx import Namespace, Resource

from ..extensions import db


ns = Namespace(
    "health",
    path="/health",
    description="check health of api and related services in a minimal way",
)


@ns.route("", doc={"produces": ["application/json"]})
class HealthResource(Resource):
    @ns.doc(responses={200: "api is healthy"})
    def get(self):
        redis_conn = current_celery_app.backend.client
        assert isinstance(redis_conn, redis.client.Redis)  # type guard
        redis_conn.ping()
        _ = db.session.execute(sa.text("SELECT 1")).scalar()
        return "OK"
