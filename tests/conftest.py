import json
import pathlib
import shutil

import pytest

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
def app(tmp_path_factory):
    """Create and configure a new app instance, once per test session."""
    app = create_app("test")
    # HACK! we should provide a way to customize config before as input to app creation
    app.config.FULLTEXT_UPLOADS_DIR = str(tmp_path_factory.mktemp("colandr_fulltexts"))
    app.config["FULLTEXT_UPLOADS_DIR"] = app.config.FULLTEXT_UPLOADS_DIR
    # TODO: don't use a globally applied app context as here, only scope minimally
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def db(app, seed_data, request):
    extensions.db.drop_all()
    extensions.db.create_all()
    _store_upload_files(app, seed_data, request)
    _populate_db(extensions.db, seed_data)
    return extensions.db


def _populate_db(db, seed_data):
    for record in seed_data["users"]:
        user = models.User(**record)
        user.password = extensions.guard.hash_password(user.password)
        db.session.add(user)
    for record in seed_data["reviews"]:
        db.session.add(models.Review(**record))
    for record in seed_data["review_plans"]:
        # NOTE: this automatically adds the relationship to associated review
        _ = models.ReviewPlan(**record)
    for record in seed_data["data_sources"]:
        db.session.add(models.DataSource(**record))
    for record in seed_data["studies"]:
        db.session.add(models.Study(**record))
    for record in seed_data["citations"]:
        db.session.add(models.Citation(**record))
    db.session.commit()
    for record in seed_data["citation_screenings"]:
        db.session.add(models.CitationScreening(**record))
    for record in seed_data["fulltext_uploads"]:
        fulltext = db.session.query(models.Fulltext).get(record["id"])
        for key, val in record.items():
            if key != "id":
                setattr(fulltext, key, val)
    # # TODO: figure out why this doesn't work :/
    # for record in seed_data["review_teams"]:
    #     review = db.session.query(models.Review).get(record["id"])
    #     user = db.session.query(models.User).get(record["user_id"])
    #     if record["action"] == "add":
    #         review.users.append(user)
    #     else:
    #         raise ValueError()
    db.session.commit()


def _store_upload_files(app, seed_data, request):
    for record in seed_data["fulltext_uploads"]:
        src_file_path = (
            request.config.rootpath / "tests" / "fixtures" / record["original_filename"]
        )
        tgt_file_path = pathlib.Path(app.config.FULLTEXT_UPLOADS_DIR).joinpath(
            str(record.get("review_id", 1)),  # HACK
            record["filename"],
        )
        tgt_file_path.parent.mkdir(exist_ok=True)
        shutil.copy(src_file_path, tgt_file_path)


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
    return user


@pytest.fixture
def admin_headers(admin_user):
    return extensions.guard.pack_header_for_user(admin_user)
