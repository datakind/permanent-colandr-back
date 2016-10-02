from flask import current_app
from flask_mail import Message

from . import celery, mail
from .models import db, User


@celery.task
def send_email(recipients, subject, text_body, html_body):
    msg = Message(current_app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)


@celery.task
def remove_unconfirmed_user(email):
    user = db.session.query(User).filter_by(email=email).one_or_none()
    if user and user.is_confirmed is False:
        db.session.delete(user)
        db.session.commit()
