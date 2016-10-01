import os
import shutil

from flask_script import Manager, prompt_bool
from flask_migrate import MigrateCommand

from colandr import create_app, db
from colandr.models import User
from colandr.config import config


manager = Manager(create_app)
manager.add_option(
    '-c', '--config', dest='config_name', type=str,
    choices=sorted(config.keys()),
    default=os.getenv('COLANDR_FLASK_CONFIG') or 'default')

manager.add_command('db', MigrateCommand)


@manager.command
def reset_db(add_admin=True):
    """
    Drop and then create all tables in the database, clear out all uploaded
    fulltext files on disk, and optionally create an admin user.
    """
    if prompt_bool("Are you sure you want to reset all db data?") is False:
        return
    db.drop_all()
    db.drop_all()
    db.create_all()
    shutil.rmtree(manager.app.config['FULLTEXT_UPLOAD_FOLDER'])
    os.makedirs(manager.app.config['FULLTEXT_UPLOAD_FOLDER'], exist_ok=True)
    if add_admin is True:
        user = User('ADMIN', 'burtdewilde@gmail.com', 'password')
        user.is_confirmed = True
        user.is_admin = True
        db.session.add(user)
        db.session.commit()


if __name__ == '__main__':
    manager.run()
