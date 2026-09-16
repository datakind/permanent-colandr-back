import contextlib

import flask
import sqlalchemy.orm as sa_orm

from colandr import models
from colandr.api.v1 import authn


@contextlib.contextmanager
def set_current_user(user: int | models.User, db_session: sa_orm.scoped_session):
    orig_user = getattr(flask.g, "current_user", None)
    user_id = user.id if isinstance(user, models.User) else user
    new_user = db_session.get(models.User, user_id)
    flask.g.current_user = new_user

    yield new_user

    flask.g.current_user = orig_user


class APIClient:
    """Wraps Flask test client with auth/context plumbing.

    Two modes, controlled by whether ``as_user()`` has been called:
    - "Admin mode": uses the session-scoped ``admin_headers`` fixture; every request
      is authenticated as user id=1
    - "User mode": calls ``as_user(user_id)`` first, and subsequent requests enter
      an app-context, temporarily set ``flask.g.current_user`` via ``set_current_user``,
      pack fresh Authorization headers, and issue the request inside that context

    File uploads are handled by passing ``files={...}`` to post() instead of ``json=...``.
    """

    def __init__(self, client, app, db_session, admin_headers):
        self._client = client
        self._app = app
        self._db_session = db_session
        self._admin_headers = admin_headers
        self._user = None

    def as_user(self, user: int | models.User):
        """Switch to "user mode" for the next request(s)."""
        self._user = user
        return self

    def get(self, endpoint, **url_params):
        return self._dispatch("get", endpoint, **url_params)

    def put(self, endpoint, *, json=None, **url_params):
        return self._dispatch("put", endpoint, json=json, **url_params)

    def post(self, endpoint, *, json=None, files=None, **url_params):
        return self._dispatch("post", endpoint, json=json, files=files, **url_params)

    def delete(self, endpoint, **url_params):
        return self._dispatch("delete", endpoint, **url_params)

    def _dispatch(self, method, endpoint, json=None, files=None, **url_params):
        with self._app.test_request_context():
            url = flask.url_for(endpoint, **url_params)

        if self._user is None:
            return self._send(method, url, self._admin_headers, json, files)

        with contextlib.ExitStack() as stack:
            # NOTE: a nested app context triggers flask-sqlalchemy's teardown_appcontext
            # -> db.session.remove(), which closes the test's savepoint session
            # and rolls back factory-created rows; so only push one when we're not
            # already inside a (fixture-provided) app context
            if not flask.has_app_context():
                stack.enter_context(self._app.app_context())
            with set_current_user(self._user, self._db_session) as user:
                headers = authn.pack_header_for_user(user)
                return self._send(method, url, headers, json, files)

    def _send(self, method, url, headers, json_body, files):
        kwargs = {"headers": headers}
        if files is not None:
            kwargs["data"] = files
        elif json_body is not None:
            kwargs["json"] = json_body
        return getattr(self._client, method)(url, **kwargs)
