import datetime

import flask_jwt_extended as jwtext
import pytest

from colandr import models
from colandr.apis import auth


@pytest.mark.parametrize("user_id", [2, 3])
def test_get_user_from_token(user_id, db_session):
    orig_user = db_session.get(models.User, user_id)
    token = jwtext.create_access_token(
        identity=orig_user, fresh=True, expires_delta=datetime.timedelta(seconds=30)
    )
    user = auth.get_user_from_token(token)
    assert user is orig_user


@pytest.mark.parametrize("user_id", [2, 3])
def test_pack_header_for_user(user_id, db_session):
    user = db_session.get(models.User, user_id)
    header = auth.pack_header_for_user(user)
    assert isinstance(header, dict)
    assert "Authorization" in header
    assert header["Authorization"].startswith("Bearer")
