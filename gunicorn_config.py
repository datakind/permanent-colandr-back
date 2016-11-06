# import multiprocessing

bind = '0.0.0.0:5000'
workers = 2  # multiprocessing.cpu_count()
worker_class = 'sync'
timeout = 30
reload = False
pidfile = './colandr.pid'
daemon = False  # in prod, should be True
