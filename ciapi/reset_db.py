from ciapi.app import app
from ciapi.models import db


if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
