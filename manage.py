import os
import shutil

from flask_script import Manager, prompt_bool
from flask_migrate import MigrateCommand

from colandr import create_app, db
from colandr.models import User
from colandr.config import configs


manager = Manager(create_app)
manager.add_option(
    '-c', '--config', dest='config_name', type=str,
    choices=sorted(configs.keys()),
    default=os.getenv('COLANDR_FLASK_CONFIG', 'default'))

manager.add_command('db', MigrateCommand)


@manager.command
def reset():
    """
    Drop and then create all tables in the database, clear out all uploaded
    fulltext files and ranking models on disk, and create an admin user.
    """
    if prompt_bool("Are you sure you want to reset ALL app data?") is False:
        return
    db.drop_all()
    db.create_all()
    for dirkey in ('FULLTEXT_UPLOADS_DIR', 'RANKING_MODELS_DIR'):
        shutil.rmtree(manager.app.config[dirkey], ignore_errors=True)
        os.makedirs(manager.app.config[dirkey], exist_ok=True)


@manager.option('-n', '--name', dest='name', required=True)
@manager.option('-e', '--email', dest='email', required=True)
@manager.option('-p', '--password', dest='password', required=True)
def add_admin(name, email, password):
    """
    Add an admin account to the database, with both `is_admin` and `is_confirmed`
    values already set to True.
    """
    user = User(name, email, password)
    user.is_confirmed = True
    user.is_admin = True
    db.session.add(user)
    try:
        db.session.commit()
    except Exception as e:
        print('an error occurred when adding admin: {}'.format(e))
        db.session.rollback()


if __name__ == '__main__':
    manager.run()
