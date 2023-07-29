#!/usr/bin/env python
import os

from colandr.app import create_app


config_name = os.getenv("COLANDR_FLASK_CONFIG") or "default"
app = create_app(config_name)
celery_app = app.extensions["celery"]
