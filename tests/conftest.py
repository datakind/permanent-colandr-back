import json
import pathlib
import shutil
from typing import Any

import flask
import flask_sqlalchemy
import pytest

from colandr import cli, extensions, models
from colandr.apis import auth
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
def app(tmp_path_factory):
    """Create and configure a new app instance, once per test session."""
    config_overrides = {
        "TESTING": True,
        "SQLALCHEMY_ECHO": True,
        "FULLTEXT_UPLOADS_DIR": str(tmp_path_factory.mktemp("colandr_fulltexts")),
    }
    app = create_app(config_overrides)
    # TODO: don't use a globally applied app context as here, only scope minimally
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def seed_data_fpath() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures" / "seed_data.json"


@pytest.fixture(scope="session")
def seed_data(seed_data_fpath: pathlib.Path) -> dict[str, Any]:
    with seed_data_fpath.open(mode="r") as f:
        seed_data = json.load(f)
    return seed_data


@pytest.fixture(scope="session")
def db(
    app: flask.Flask, seed_data_fpath: pathlib.Path, seed_data: dict[str, Any], request
):
    extensions.db.drop_all()
    extensions.db.create_all()
    _store_upload_files(app, seed_data, request)
    app.test_cli_runner().invoke(cli.db_seed, ["--fpath", str(seed_data_fpath)])
    return extensions.db


def _store_upload_files(app: flask.Flask, seed_data: dict[str, Any], request):
    for record in seed_data["fulltext_uploads"]:
        src_file_path = (
            request.config.rootpath / "tests" / "fixtures" / record["original_filename"]
        )
        tgt_file_path = pathlib.Path(app.config["FULLTEXT_UPLOADS_DIR"]).joinpath(
            str(record.get("review_id", 1)),  # HACK
            record["filename"],
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
    Allow very fast tests by using rollbacks and nested sessions. This does
    require that your database supports SQL savepoints, and Postgres does.
    """
    db.session.begin_nested()

    yield db.session

    db.session.rollback()


@pytest.fixture(scope="session")
def admin_user(db: flask_sqlalchemy.SQLAlchemy):
    user = db.session.get(models.User, 1)
    return user


@pytest.fixture
def admin_headers(admin_user: models.User):
    return auth.pack_header_for_user(admin_user)
