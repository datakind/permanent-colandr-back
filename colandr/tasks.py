from flask import current_app
from flask_mail import Message

from . import celery, mail


@celery.task
def send_email(recipients, subject, text_body, html_body):
    app = current_app  #._get_current_object()
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['MAIL_DEFAULT_SENDER'],
                  recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)
