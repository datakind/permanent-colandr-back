import pytest

from colandr.app import create_app
from colandr.extensions import db


@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance, once per test session."""
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


@pytest.fixture
def cli_runner(app):
    return app.test_cli_runner()
