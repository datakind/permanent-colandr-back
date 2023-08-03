import os
import shutil

import click
from flask import Blueprint, current_app

from colandr.extensions import db, guard
from colandr.models import User


bp = Blueprint("cli", __name__, cli_group=None)


@bp.cli.command("create-db")
def create_db():
    """
    Create all tables in the database that do not already exist.
    Note: This does not update existing tables -- use `flask-migrate` commands for that.
    """
    db.create_all()


@bp.cli.command("reset-db")
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
    user = User(name=name, email=email, password=guard.hash_password(password))
    user.is_confirmed = True
    user.is_admin = True
    db.session.add(user)
    try:
        db.session.commit()
        current_app.logger.info("admin user %s added to db", user)
    except Exception as e:
        current_app.logger.error("an error occurred when adding admin: %s", e)
        db.session.rollback()
