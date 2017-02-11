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
def reset_db():
    """
    Drop and then create all tables in the database, clear out all uploaded
    fulltext files and ranking models on disk, and create an admin user.
    """
    if prompt_bool("Are you sure you want to reset ALL app data?") is False:
        return
    db.drop_all()
    db.create_all()
    for dirkey in ('FULLTEXT_UPLOAD_FOLDER', 'RANKING_MODELS_FOLDER'):
        shutil.rmtree(manager.app.config[dirkey], ignore_errors=True)
        os.makedirs(manager.app.config[dirkey], exist_ok=True)
    user = User('ADMIN', 'burtdewilde@gmail.com', 'password')
    user.is_confirmed = True
    user.is_admin = True
    db.session.add(user)
    db.session.commit()


if __name__ == '__main__':
    manager.run()
