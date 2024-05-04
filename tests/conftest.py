import json
import os
import pathlib
import shutil
import typing as t

import flask
import flask_sqlalchemy
import pytest
import sqlalchemy as sa
import sqlalchemy.orm as sa_orm
from pytest_postgresql import factories as psql_factories

from colandr import cli, extensions, models
from colandr.apis import auth
from colandr.app import create_app


TEST_DB_SCHEMA = "test"


def _init_db(**kwargs):
    db_url = sa.URL.create(
        drivername="postgresql+psycopg",
        username=kwargs["user"],
        password=kwargs["password"],
        host=kwargs["host"],
        port=kwargs["port"],
        database=kwargs["dbname"],
    )
    engine = sa.create_engine(db_url)
    # create test schema if it doesn't already exist
    with engine.begin() as conn:
        # conn.execute(sa.text('DROP DATABASE IF EXISTS "colandr_tmpl"'))
        conn.execute(sa.schema.CreateSchema(TEST_DB_SCHEMA, if_not_exists=True))

    extensions._BaseModel.metadata.create_all(engine)


psql_noproc = psql_factories.postgresql_noproc(
    host="colandr-db",
    port=5432,
    user=os.environ["COLANDR_DB_USER"],
    password=os.environ["COLANDR_DB_PASSWORD"],
    dbname=os.environ["COLANDR_DB_NAME"],
    # load=[_init_db],
)
psql = psql_factories.postgresql("psql_noproc")


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create and configure a new app instance, once per test session."""
    config_overrides = {
        "TESTING": True,
        # this overrides the app db's default schema (None => "public")
        # so that we create a parallel schema for all unit testing data
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "execution_options": {"schema_translate_map": {None: TEST_DB_SCHEMA}}
        },
        "SQLALCHEMY_ECHO": True,
        "SQLALCHEMY_RECORD_QUERIES": True,
        "FULLTEXT_UPLOADS_DIR": str(tmp_path_factory.mktemp("colandr_fulltexts")),
    }
    app = create_app(config_overrides)
    # TODO: don't use a globally applied app context as here, only scope minimally
    with app.app_context():
        yield app


@pytest.fixture
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
def db(
    app: flask.Flask,
    psql_noproc,
    seed_data_fpath: pathlib.Path,
    seed_data: dict[str, t.Any],
    request,
):
    # db_url = sa.URL.create(
    #     drivername="postgresql+psycopg",
    #     username=psql_noproc.user,
    #     password=psql_noproc.password,
    #     host=psql_noproc.host,
    #     port=psql_noproc.port,
    #     database=psql_noproc.dbname,
    # )
    # engine = sa.create_engine(db_url, echo=True)
    # with engine.begin() as conn:
    #     conn.execute(sa.schema.CreateSchema("test", if_not_exists=True))
    # # engine.update_execution_options(schema_translate_map={None: "test"})
    # session = sa_orm.scoped_session(sa_orm.sessionmaker(bind=engine))
    # extensions.db.session = session

    # drop template database if it exists
    # with extensions.db.engine.connect().execution_options(
    #     isolation_level="AUTOCOMMIT"
    # ) as conn:
    #     conn.execute(sa.text('ALTER DATABASE "colandr_tmpl" IS_TEMPLATE FALSE'))
    #     conn.execute(sa.text('DROP DATABASE IF EXISTS "colandr_tmpl"'))
    # create test schema if it doesn't already exist
    with extensions.db.engine.begin() as conn:
        conn.execute(sa.schema.CreateSchema(TEST_DB_SCHEMA, if_not_exists=True))
    # make sure we're starting fresh, tables-wise
    extensions.db.drop_all()
    extensions.db.create_all()
    _store_upload_files(app, seed_data, request)
    app.test_cli_runner().invoke(cli.db_seed, ["--fpath", str(seed_data_fpath)])

    yield extensions.db

    # extensions.db.drop_all()

    # NOTE: this doesn't work :/ the command just hangs, and if you cancel it,
    # the entire database gets borked owing to a duplicate template database
    # so, let's leave the test schema in place, it's small and causes no harm
    # with extensions.db.engine.begin() as conn:
    #     conn.execute(sa.schema.DropSchema("test", cascade=True, if_exists=True))


def _store_upload_files(app: flask.Flask, seed_data: dict[str, t.Any], request):
    for record in seed_data["studies"]:
        if not record.get("fulltext"):
            continue

        src_file_path = (
            request.config.rootpath
            / "tests"
            / "fixtures"
            / record["fulltext"]["original_filename"]
        )
        tgt_file_path = pathlib.Path(app.config["FULLTEXT_UPLOADS_DIR"]).joinpath(
            str(record.get("review_id", 1)),  # HACK
            record["fulltext"]["filename"],
        )
        tgt_file_path.parent.mkdir(exist_ok=True)
        shutil.copy(src_file_path, tgt_file_path)


@pytest.fixture
def client(app: flask.Flask):
    yield app.test_client()


@pytest.fixture
def cli_runner(app: flask.Flask):
    yield app.test_cli_runner()


@pytest.fixture
def db_session(db: flask_sqlalchemy.SQLAlchemy):
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
def admin_user(db: flask_sqlalchemy.SQLAlchemy):
    user = db.session.get(models.User, 1)
    return user


@pytest.fixture
def admin_headers(admin_user: models.User):
    return auth.pack_header_for_user(admin_user)
