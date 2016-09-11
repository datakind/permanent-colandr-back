import argparse
import os
import sys

from colandr import config, create_app


def main():
    parser = argparse.ArgumentParser(
        description='Run the colandr web app using a particular configuration.')
    parser.add_argument(
        '--config', type=str, choices=sorted(config.keys()),
        default=os.getenv('FLASK_CONFIG') or 'default')
    args = parser.parse_args()

    app = create_app(args.config)
    app.run()


if __name__ == '__main__':
    sys.exit(main())
