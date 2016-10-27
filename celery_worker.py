#!/usr/bin/env python
import os

from colandr import celery, create_app


config_name = 'dev'  # os.getenv('COLANDR_FLASK_CONFIG') or 'default'
print('app config = "{}"'.format(config_name))
app = create_app(config_name)
app.app_context().push()
