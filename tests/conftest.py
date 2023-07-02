import json
import pathlib

import pytest
from flask import g

from colandr import extensions, models
from colandr.app import create_app


# TODO: consider hacking on a solution that doesn't require a running psql db
# for example, this almost but didn't quite work
# import pytest_postgresql.factories
# psql_proc = pytest_postgresql.factories.postgresql_proc(
#     host="localhost",
#     port=5432,
#     user="colandr_app",
#     password="PASSWORD",
#     dbname="colandr",
# )
# psql_db = pytest_postgresql.factories.postgresql("psql_proc", dbname="colandr")


@pytest.fixture(scope="session")
def seed_data():
    path = pathlib.Path(__file__).parent / "fixtures" / "seed_data.json"
    with path.open(mode="r") as f:
        seed_data = json.load(f)
    return seed_data


@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance, once per test session."""
    # create the app with common test config
    app = create_app("test")
    # TODO: don't use a globally applied app context as here, only scope minimally
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def db(app, seed_data):
    extensions.db.drop_all()
    extensions.db.create_all()
    _populate_db(extensions.db, seed_data)
    return extensions.db


def _populate_db(db, seed_data):
    for record in seed_data["users"]:
        db.session.add(models.User(**record))
    for record in seed_data["reviews"]:
        db.session.add(models.Review(**record))
    db.session.commit()
    for record in seed_data["review_plans"]:
        # NOTE: this automatically adds the relationship to associated review
        review_plan = models.ReviewPlan(**record)
    # # TODO: figure out why this doesn't work :/
    # for record in seed_data["review_teams"]:
    #     review = db.session.query(models.Review).get(record["id"])
    #     user = db.session.query(models.User).get(record["user_id"])
    #     if record["action"] == "add":
    #         review.users.append(user)
    #     else:
    #         raise ValueError()
    db.session.commit()
    db.session.flush()


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture
def cli_runner(app):
    yield app.test_cli_runner()


@pytest.fixture
def db_session(db):
    """
    Allow very fast tests by using rollbacks and nested sessions. This does
    require that your database supports SQL savepoints, and Postgres does.
    """
    db.session.begin_nested()

    yield db.session

    db.session.rollback()


@pytest.fixture(scope="session")
def admin_user(db):
    user = db.session.query(models.User).get(1)
    g.current_user = user
    return user


@pytest.fixture
def admin_headers(admin_user):
    return extensions.guard.pack_header_for_user(admin_user)
