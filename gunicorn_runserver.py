#!/usr/bin/env python
import os

from colandr import create_app


config_name = os.getenv("COLANDR_FLASK_CONFIG", "default")
app = create_app(config_name)
