import multiprocessing
import os


bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
# TODO: set both to 1 in dev .env ?
workers = int(os.getenv("COLANDR_API_CONCURRENCY", multiprocessing.cpu_count() * 2))
threads = int(os.getenv("COLANDR_PYTHON_MAX_THREADS", 1))
worker_class = "sync"
timeout = 30
reload = bool(int(os.getenv("COLANDR_API_RELOAD", False)))
pidfile = "./colandr.pid"
daemon = False  # in prod, should be True?
accesslog = "-"  # log to stdout
