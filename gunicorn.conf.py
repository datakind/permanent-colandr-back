# reference: https://docs.gunicorn.org/en/stable/settings.html
import multiprocessing
import os


bind = f"0.0.0.0:{os.getenv('COLANDR_GUNICORN_PORT', '5000')}"
workers = int(os.getenv("COLANDR_GUNICORN_WORKERS", multiprocessing.cpu_count() * 2))
threads = int(os.getenv("COLANDR_GUNICORN_THREADS", "1"))
reload = bool(int(os.getenv("COLANDR_GUNICORN_RELOAD", "0")))
loglevel = os.getenv("COLANDR_GUNICORN_LOG_LEVEL", "info")
accesslog = "-"  # log to stdout
pidfile = "./colandr.pid"

# TODO
# daemon = False or True? does that depend on env?
