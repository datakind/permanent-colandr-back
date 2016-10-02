#!/usr/bin/env python
import os
from colandr import celery, create_app

config_name = os.getenv('COLANDR_FLASK_CONFIG') or 'default'
app = create_app(config_name)
app.app_context().push()
