import multiprocessing
import os


bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = multiprocessing.cpu_count()
worker_class = "sync"
timeout = 30
reload = False
pidfile = "./colandr.pid"
daemon = False  # in prod, should proably be True
accesslog = "-"
