#!/usr/bin/env python
from colandr.app import create_app


app = create_app()
celery_app = app.extensions["celery"]
