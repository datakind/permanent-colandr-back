from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['PASSWORD_SALT'])


def confirm_token(token, max_age='default'):
    """
    Args:
        token (str)
        max_age (int or str): If "default", value is set to current app's config
            ``CONFIRM_TOKEN_EXPIRATION``. If false-y, no max age is used.

    Returns:
        str
    """
    if max_age == 'default':
        max_age = current_app.config['CONFIRM_TOKEN_EXPIRATION']
    elif not max_age:
        max_age = None
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token, salt=current_app.config['PASSWORD_SALT'], max_age=max_age)
        return email
    except Exception:
        return False
