import sqlalchemy as sa

from colandr.extensions import db


def test_db_connection(app):
    with app.app_context():
        with db.engine.connect() as conn:
            _ = conn.execute(sa.text("SELECT 1"))
