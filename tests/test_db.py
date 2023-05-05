import pytest

from colandr import db


def test_get_close_db(app):
    with app.app_context():
        db.engine.execute("SELECT 1")
