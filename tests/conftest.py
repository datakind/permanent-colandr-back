import os
import pathlib

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
from tests import factories


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
def client(app: flask.Flask):
    return app.test_client()


@pytest.fixture(scope="session")
def cli_runner(app: flask.Flask):
    return app.test_cli_runner()


@pytest.fixture(scope="session")
def db(app: flask.Flask, psql_noproc):
    with app.app_context():
        # create test database if it doesn't already exist
        if not sa_utils.database_exists(extensions.db.engine.url):
            sa_utils.create_database(extensions.db.engine.url)
        # make sure we're starting fresh, tables-wise
        extensions.db.drop_all()
        extensions.db.create_all()

    yield extensions.db

    # NOTE: none of these cleanup commands work :/ it just hangs, and if you cancel it,
    # the entire database could get borked owing to a duplicate template database
    # so, let's leave test data in place, it's small and causes no harm
    # extensions.db.drop_all()
    # sa_utils.drop_database(extensions.db.engine.url)


def _reset_db_world(db: flask_sqlalchemy.SQLAlchemy, app: flask.Flask) -> None:
    """Reset the DB to a known-empty state: no rows, sequences at 1, no uploads.

    The uploads directories are cleared too, because ``RESTART IDENTITY`` recycles
    review/study ids: without this, a module that recreates review id 1 could
    read or clobber fulltext files and citation imports left behind by an earlier one.
    """
    with app.app_context():
        # TRUNCATE needs an exclusive lock on every table, and this runs in its own
        # app context, so a read transaction left open by an earlier test would block it
        # indefinitely -- time out instead, and fail loudly with a lock error
        db.session.execute(sa.text("SET LOCAL lock_timeout = '10s'"))
        table_names = ", ".join(table.name for table in db.metadata.sorted_tables)
        db.session.execute(sa.text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
        db.session.commit()
        filesystem = app.extensions["filesystem"]
        for dirkey in ("FULLTEXT_UPLOADS_DIR", "CITATION_UPLOADS_DIR"):
            uploads_dir = app.config[dirkey]
            if filesystem.exists(uploads_dir):
                filesystem.rm(uploads_dir, recursive=True)
            filesystem.makedirs(uploads_dir, exist_ok=True)


@pytest.fixture(scope="module")
def db_empty(db: flask_sqlalchemy.SQLAlchemy, app: flask.Flask):
    """World: all tables present, zero rows, exactly one admin user.

    The admin is part of the world contract rather than a side effect of the
    ``api`` fixture, so every module starts from the same documented state and
    "the DB holds only what I created" stays true apart from that one row.
    """
    _reset_db_world(db, app)
    with app.app_context():
        factories.create_user(db.session, name="Admin User", is_admin=True)
        db.session.commit()  # tests run in savepoints on another connection


@pytest.fixture(scope="module")
def db_seeded(db, app, cli_runner, seed_data_fpath):
    """World: the full seed dataset, loaded through ``flask db-seed``.

    Only ``tests/api/test_smoke.py`` uses this world; every other module builds its
    own state with factories in ``db_empty``. This only seeds db rows (no on-disk files).
    ``db-seed`` resyncs the id sequences itself, so creating rows in this world is safe.
    """
    _reset_db_world(db, app)
    cli_runner.invoke(cli.db_seed, ["--fpath", str(seed_data_fpath)])


@pytest.fixture
def db_session(db: flask_sqlalchemy.SQLAlchemy, app_ctx):
    """
    Automatically roll back database changes occurring within tests,
    so side-effects of one test don't affect another.
    """
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


@pytest.fixture
def admin_user(db_session):
    """The current world's admin: `db_empty` created one, `db_seeded` has user 1."""
    admin = (
        db_session.execute(
            sa.select(models.User).filter_by(is_admin=True).order_by(models.User.id)
        )
        .scalars()
        .first()
    )
    if admin is None:
        raise LookupError(
            "no admin in this world -- is the module missing its world marker "
            '(pytest.mark.usefixtures("db_empty") or "db_seeded")?'
        )
    return admin


@pytest.fixture
def admin_headers(admin_user: models.User, app_ctx):
    return authn.pack_header_for_user(admin_user)


@pytest.fixture
def api(client, app, db_session, admin_headers):
    """Pre-configured APIClient for API-level tests."""
    from .helpers import APIClient

    return APIClient(client, app, db_session, admin_headers)


@pytest.fixture(autouse=True)
def clear_app_state(app, app_ctx):
    """Clear app-level caches around each test, and close the app-context session after.

    Caches must go because ids repeat across worlds. The db session must go to avoid
    locks that could block the next world's TRUNCATE statement.
    """
    for cache in (extensions.cache, extensions.review_model_cache):
        cache.clear()
    yield
    for cache in (extensions.cache, extensions.review_model_cache):
        cache.clear()
    extensions.db.session.remove()
