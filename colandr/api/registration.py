from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['PASSWORD_SALT'])


def confirm_token(token, max_age=current_app.config['CONFIRM_TOKEN_EXPIRATION']):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token, salt=current_app.config['PASSWORD_SALT'], max_age=max_age)
        return email
    except Exception:
        return False
