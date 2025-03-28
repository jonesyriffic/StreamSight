#!/bin/bash

# Start script for NextGen Insight Spark with increased file upload limits
echo "Starting NextGen Insight Spark with 100MB file upload support..."

# Create the temporary upload directory if it doesn't exist
mkdir -p uploads
chmod 755 uploads

# Set environment variables
export WERKZEUG_SERVER_MAX_CONTENT_LENGTH=104857600  # 100MB in bytes

# Start the application with Gunicorn
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload \
  --timeout 300 \
  --limit-request-line 0 \
  --limit-request-fields 0 \
  --limit-request-field-size 0 \
  --worker-class gthread \
  --threads 4 \
  --config gunicorn.conf.py \
  main:app