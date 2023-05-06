import pytest

from colandr import create_app, db


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # create the app with common test config
    app = create_app("test")
    # reset database data
    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app


@pytest.fixture
def client(app):
    return app.test_client()
