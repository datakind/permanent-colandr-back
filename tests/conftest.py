import json
import os
import pathlib
import typing as t

import flask
import flask_sqlalchemy
import pytest
import sqlalchemy as sa
import sqlalchemy.orm as sa_orm
import sqlalchemy_utils as sa_utils
from pytest_postgresql import factories as psql_factories

from colandr import cli, extensions, models
from colandr.api.v1 import authn
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
        "SQLALCHEMY_ECHO": False,
        "SQLALCHEMY_RECORD_QUERIES": True,
        # local filesystem
        "FILESYSTEM_PROTOCOL": "file",
        "RANKER_MODELS_DIR": str(tmp_path_factory.mktemp("colandr_ranker_models")),
        "FULLTEXT_UPLOADS_DIR": str(tmp_path_factory.mktemp("colandr_fulltexts")),
        "CITATION_UPLOADS_DIR": str(tmp_path_factory.mktemp("colandr_citations")),
        # (fake-)gcs filesystem
        # "FILESYSTEM_PROTOCOL": "gcs",
        # "FILESYSTEM_GCS_PROJECT": "test-project",
        # "FILESYSTEM_ROOT_DIR": "test-bucket",
        # "FILESYSTEM_GCS_TOKEN": "anon",
        # disable rate-limiting, so we can test at high speed
        "RATELIMIT_ENABLED": False,
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
        tgt_file_path = os.path.join(
            app.config["FULLTEXT_UPLOADS_DIR"],
            str(record.get("review_id", 1)),
            record["fulltext"]["filename"],
        )
        fs = app.extensions["filesystem"]
        fs.makedirs(os.path.dirname(tgt_file_path), exist_ok=True)
        fs.put_file(src_file_path, tgt_file_path)


@pytest.fixture
def db_session(db: flask_sqlalchemy.SQLAlchemy, app: flask.Flask):
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        # flask-sqlalchemy stores per-app engine maps in db._app_engines[app]
        # .engines property reads from this dict but has no setter
        # so mutate the dict in place to swap in our static-connection shim
        app_engines = db._app_engines[app]
        original_default_engine = app_engines[None]
        app_engines[None] = _StaticConnEngine(connection)
        session_factory = sa_orm.sessionmaker(
            bind=connection, join_transaction_mode="create_savepoint"
        )
        session = sa_orm.scoped_session(session_factory)
        original_session = db.session
        db.session = session

        try:
            yield session
        finally:
            session.remove()
            db.session = original_session
            app_engines[None] = original_default_engine
            transaction.rollback()
            connection.close()


@pytest.fixture
def admin_user(db_session):
    return db_session.get(models.User, 1)


@pytest.fixture
def admin_headers(admin_user):
    return authn.pack_header_for_user(admin_user)


class _StaticConnEngine:
    """Engine shim that hands out the same connection on every .connect() call."""

    def __init__(self, conn: sa.Connection):
        self._conn = conn
        self._static = _StaticConnection(conn)

    def connect(self):
        return self._static

    def __getattr__(self, name):
        # delegate everything else (url, dialect, name, etc.) to the real engine
        return getattr(self._conn.engine, name)


class _StaticConnection:
    """Wraps a Connection so .close() is a no-op; delegates everything else."""

    def __init__(self, conn: sa.Connection):
        self._conn = conn

    def close(self):  # neutralized — fixture owns the real close
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass  # don't close on context-manager exit either
