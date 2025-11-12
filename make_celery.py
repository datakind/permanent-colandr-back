#!/usr/bin/env python
from colandr.app import create_app_v1_1


app = create_app_v1_1()
celery_app = app.extensions["celery"]
