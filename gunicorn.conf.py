# reference: https://docs.gunicorn.org/en/stable/settings.html
import multiprocessing
import os


bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
worker_class = "sync"
workers = int(os.getenv("COLANDR_GUNICORN_WORKERS", multiprocessing.cpu_count() * 2))
threads = int(os.getenv("COLANDR_GUNICORN_THREADS", 1))
reload = bool(int(os.getenv("COLANDR_GUNICORN_RELOAD", False)))
pidfile = "./colandr.pid"
daemon = False  # TODO: in prod, should be True?
accesslog = "-"
loglevel = os.getenv("COLANDR_GUNICORN_LOG_LEVEL", "info")
