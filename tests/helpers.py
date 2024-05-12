import contextlib

import flask
import sqlalchemy.orm as sa_orm

from colandr import models


@contextlib.contextmanager
def set_current_user(user_id: int, db_session: sa_orm.scoped_session):
    orig_user = getattr(flask.g, "current_user", None)
    new_user = db_session.get(models.User, user_id)
    assert new_user is not None
    flask.g.current_user = new_user

    yield new_user

    flask.g.current_user = orig_user
