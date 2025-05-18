import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = 'logs/access.log'
errorlog = 'logs/error.log'
loglevel = 'info'

# Process naming
proc_name = 'cms'

# SSL (uncomment and configure if using HTTPS)
# keyfile = 'path/to/keyfile'
# certfile = 'path/to/certfile'

# Server mechanics
daemon = False
pidfile = 'logs/gunicorn.pid'
umask = 0
user = None
group = None
tmp_upload_dir = None

# Server hooks
def on_starting(server):
    """
    Server startup hook
    """
    pass

def on_exit(server):
    """
    Server exit hook
    """
    pass

def worker_int(worker):
    """
    Worker interrupt hook
    """
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    """
    Worker abort hook
    """
    worker.log.info("worker received SIGABRT signal") 