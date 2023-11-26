import json
import os
import pathlib
import shutil

import alembic.command
import alembic.config
import click
from flask import Blueprint, current_app

from colandr import models
from colandr.extensions import db
from colandr.models import User


bp = Blueprint("cli", __name__, cli_group=None)


@bp.cli.command("db-create")
def db_create():
    """
    Create all tables in the database that do not already exist,
    and stamp alembic version "head" with the latest available revision.

    Reference:
        https://alembic.sqlalchemy.org/en/latest/cookbook.html#building-an-up-to-date-database-from-scratch

    Note:
        This does not update existing tables -- use `flask-migrate` commands for that.
    """
    db.create_all()
    alembic_cfg = alembic.config.Config(
        pathlib.Path(current_app.root_path).parent / "migrations" / "alembic.ini"
    )
    alembic.command.stamp(alembic_cfg, "head")


@bp.cli.command("db-seed")
@click.option("--fpath", "file_path", type=pathlib.Path, required=True)
def db_seed(file_path: pathlib.Path):
    """
    Populate tables in the current app's database with records from a seed data file,
    saved in json format.
    """
    with file_path.resolve().open(mode="r") as f:
        data = json.load(f)

    current_app.logger.info(
        "seeding database with %s records loaded from %s ...",
        list(data.keys()),
        file_path,
    )
    for record in data["users"]:
        db.session.add(models.User(**record))
    for record in data["reviews"]:
        db.session.add(models.Review(**record))
    for record in data["data_sources"]:
        db.session.add(models.DataSource(**record))
    for record in data["imports"]:
        db.session.add(models.Import(**record))
    for record in data["studies"]:
        db.session.add(models.Study(**record))
    for record in data["citations"]:
        db.session.add(models.Citation(**record))
    db.session.commit()
    # empty review plans already created w/ review
    for record in data["review_plans"]:
        plan = db.session.get(models.ReviewPlan, record["id_"])
        for key, val in record.items():
            if key != "id_":
                setattr(plan, key, val)
    for record in data["citation_screenings"]:
        db.session.add(models.CitationScreening(**record))
    for record in data["fulltext_uploads"]:
        fulltext = db.session.get(models.Fulltext, record["id"])
        for key, val in record.items():
            if key != "id":
                setattr(fulltext, key, val)
    for record in data["fulltext_screenings"]:
        db.session.add(models.FulltextScreening(**record))
    # # TODO: figure out why this doesn't work :/
    # for record in seed_data["review_teams"]:
    #     review = db.session.get(models.Review, record["id"])
    #     user = db.session.get(models.User, record["user_id"])
    #     if record["action"] == "add":
    #         review.users.append(user)
    #     else:
    #         raise ValueError()
    db.session.commit()


@bp.cli.command("db-reset")
def reset_db():
    """
    Drop and then create all tables in the database, clear out all uploaded
    fulltext files and ranking models on disk, and create an admin user.
    """
    click.confirm("Are you sure you want to reset ALL app data?", abort=True)
    current_app.logger.warning("resetting database ...")
    db.drop_all()
    db.create_all()
    for dirkey in ("FULLTEXT_UPLOADS_DIR", "RANKING_MODELS_DIR"):
        shutil.rmtree(current_app.config[dirkey], ignore_errors=True)
        os.makedirs(current_app.config[dirkey], exist_ok=True)


@bp.cli.command("add-admin")
@click.option("-n", "--name", "name", type=str, required=True)
@click.option("-e", "--email", type=str, required=True)
@click.option(
    "-p",
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    type=str,
    required=True,
)
def add_admin(name, email, password):
    """
    Add an admin account to the database, with both `is_admin` and `is_confirmed`
    values already set to True.
    """
    user = User(name=name, email=email, password=password)
    user.is_confirmed = True
    user.is_admin = True
    db.session.add(user)
    try:
        db.session.commit()
        current_app.logger.info("admin user %s added to db", user)
    except Exception as e:
        current_app.logger.error("an error occurred when adding admin: %s", e)
        db.session.rollback()
