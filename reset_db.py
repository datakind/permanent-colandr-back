import argparse
import os
import sys

from colandr import create_app, db


def main():
    parser = argparse.ArgumentParser(
        description='Reset the colandr database using a particular configuration.')
    parser.add_argument(
        '--config', '-c', type=str,
        default=os.getenv('FLASK_CONFIG') or 'default')
    args = parser.parse_args()

    app = create_app(args.config)
    with app.app_context():
        db.drop_all()
        db.create_all()


if __name__ == '__main__':
    sys.exit(main())
