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
        # TODO: redis.ping() ?
        db.engine.execute("SELECT 1")
        return "OK"
