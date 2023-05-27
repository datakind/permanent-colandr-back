from colandr import db


def test_db_connection(app):
    with app.app_context():
        db.engine.execute("SELECT 1")
