# reference: https://docs.gunicorn.org/en/stable/settings.html
import multiprocessing
import os


bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2))
threads = int(os.getenv("COLANDR_GUNICORN_THREADS", 1))
worker_class = "sync"
reload = bool(int(os.getenv("COLANDR_GUNICORN_RELOAD", False)))
pidfile = "./colandr.pid"
daemon = False  # in prod, should be True?
accesslog = "-"  # log to stdout
loglevel = os.getenv("COLANDR_LOG_LEVEL", "info")
