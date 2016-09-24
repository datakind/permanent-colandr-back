import argparse
import os
import shutil
import sys

from colandr import config, create_app, db


def main():
    parser = argparse.ArgumentParser(
        description='Reset the colandr database using a particular configuration.')
    parser.add_argument(
        '--config', type=str, choices=sorted(config.keys()),
        default=os.getenv('FLASK_CONFIG') or 'default')
    args = parser.parse_args()

    app = create_app(args.config)
    with app.app_context():
        db.drop_all()
        db.create_all()
        shutil.rmtree(app.config['FULLTEXT_UPLOAD_FOLDER'])


if __name__ == '__main__':
    sys.exit(main())
