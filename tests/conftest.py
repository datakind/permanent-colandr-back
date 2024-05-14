import json
import os
import pathlib
import shutil
import typing as t

import flask
import flask_sqlalchemy
import pytest
import sqlalchemy.orm as sa_orm
import sqlalchemy_utils as sa_utils
from pytest_postgresql import factories as psql_factories

from colandr import cli, extensions, models
from colandr.apis import auth
from colandr.app import create_app


TEST_DBNAME = "colandr_test"

psql_noproc = psql_factories.postgresql_noproc(
    host=os.environ.get("COLANDR_DB_HOST", "colandr-db"),
    port=5432,
    user=os.environ["COLANDR_DB_USER"],
    password=os.environ["COLANDR_DB_PASSWORD"],
    dbname=TEST_DBNAME,  # override os.environ["COLANDR_DB_NAME"]
)
psql = psql_factories.postgresql("psql_noproc")


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create and configure a new app instance, once per test session."""
    config_overrides = {
        "TESTING": True,
        # override db uri to point at test database
        "SQLALCHEMY_DATABASE_URI": (
            "postgresql+psycopg://"
            f"{os.environ['COLANDR_DB_USER']}:{os.environ['COLANDR_DB_PASSWORD']}"
            f"@{os.environ.get('COLANDR_DB_HOST', 'colandr-db')}:5432/{TEST_DBNAME}"
        ),
        "SQLALCHEMY_ECHO": True,
        "SQLALCHEMY_RECORD_QUERIES": True,
        "FULLTEXT_UPLOADS_DIR": str(tmp_path_factory.mktemp("colandr_fulltexts")),
    }
    app = create_app(config_overrides)
    return app


@pytest.fixture(scope="session")
def app_ctx(app):
    with app.app_context():
        yield


@pytest.fixture(scope="session")
def seed_data_fpath() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures" / "seed_data.json"


@pytest.fixture(scope="session")
def seed_data(seed_data_fpath: pathlib.Path) -> dict[str, t.Any]:
    with seed_data_fpath.open(mode="r") as f:
        seed_data = json.load(f)
    return seed_data


@pytest.fixture(scope="session")
def client(app: flask.Flask):
    return app.test_client()


@pytest.fixture(scope="session")
def cli_runner(app: flask.Flask):
    return app.test_cli_runner()


@pytest.fixture(scope="session")
def db(
    app: flask.Flask,
    cli_runner,
    seed_data_fpath: pathlib.Path,
    seed_data: dict[str, t.Any],
    psql_noproc,
    request,
):
    with app.app_context():
        # create test database if it doesn't already exist
        if not sa_utils.database_exists(extensions.db.engine.url):
            sa_utils.create_database(extensions.db.engine.url)
        # make sure we're starting fresh, tables-wise
        extensions.db.drop_all()
        extensions.db.create_all()

    _store_upload_files(app, seed_data, request)
    cli_runner.invoke(cli.db_seed, ["--fpath", str(seed_data_fpath)])

    yield extensions.db

    # NOTE: none of these cleanup commands work :/ it just hangs, and if you cancel it,
    # the entire database could get borked owing to a duplicate template database
    # so, let's leave test data in place, it's small and causes no harm
    # extensions.db.drop_all()
    # sa_utils.drop_database(extensions.db.engine.url)


def _store_upload_files(app: flask.Flask, seed_data: dict[str, t.Any], request):
    for record in seed_data["studies"]:
        if not record.get("fulltext"):
            continue

        src_file_path = (
            request.config.rootpath
            / "tests"
            / "fixtures"
            / "fulltexts"
            / record["fulltext"]["original_filename"]
        )
        tgt_file_path = pathlib.Path(app.config["FULLTEXT_UPLOADS_DIR"]).joinpath(
            str(record.get("review_id", 1)),  # HACK
            record["fulltext"]["filename"],
        )
        tgt_file_path.parent.mkdir(exist_ok=True)
        shutil.copy(src_file_path, tgt_file_path)


@pytest.fixture
def db_session(db: flask_sqlalchemy.SQLAlchemy, app_ctx):
    """
    Automatically roll back database changes occurring within tests,
    so side-effects of one test don't affect another.
    """
    # this no longer works in sqlalchemy v2.0 :/
    # db.session.begin_nested()
    # yield db.session
    # db.session.rollback()
    # but this more complex setup apparently works in v2.0
    # which is a recurring theme ... sqlalchemy v2.0 is harder to use somehow
    conn = db.engine.connect()
    transaction = conn.begin()
    orig_session = db.session
    session_factory = sa_orm.sessionmaker(
        bind=conn, join_transaction_mode="create_savepoint"
    )
    session = sa_orm.scoped_session(session_factory)
    db.session = session

    yield db.session

    session.close()
    transaction.rollback()
    conn.close()
    db.session = orig_session


@pytest.fixture(scope="session")
def admin_user(db: flask_sqlalchemy.SQLAlchemy, app_ctx):
    user = db.session.get(models.User, 1)
    return user


@pytest.fixture(scope="session")
def admin_headers(admin_user: models.User, app_ctx):
    return auth.pack_header_for_user(admin_user)
