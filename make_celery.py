#!/usr/bin/env python
from colandr.app import create_app_v1


app = create_app_v1()
celery_app = app.extensions["celery"]
