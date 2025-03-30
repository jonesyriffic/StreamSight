# Gunicorn configuration file for large file uploads

# Binding
bind = "0.0.0.0:5000"

# Worker processes
workers = 1
threads = 2

# Timeouts 
timeout = 300  # 5 minutes - increased for large file uploads
keepalive = 5

# Server mechanics
daemon = False
reload = True
reuse_port = True

# Logging
loglevel = "info"
accesslog = "-"  # stdout
errorlog = "-"   # stderr

# Large request handling
limit_request_line = 0       # 0 = unlimited
limit_request_fields = 0     # 0 = unlimited
limit_request_field_size = 0 # 0 = unlimited

# Maximum request body size (100MB - important!)
# We need to make sure we don't time out before completing large uploads
worker_class = "gthread"
worker_connections = 1000

# Increase buffer size for large request bodies
# This helps handle large file uploads through Gunicorn
# Note: We can't directly set max body size in Gunicorn, handled by Flask's MAX_CONTENT_LENGTH

# Python-specific settings for large file handling
post_fork = lambda server, worker: worker.log.info("Worker spawned (pid: %s)", worker.pid)
post_worker_init = lambda worker: worker.log.info("Worker initialized with large file support")