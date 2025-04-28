#!/bin/sh

# Abort on any error (including if wait-for-it fails).
set -e

# Wait for the backend to be up, if we know where it is.
if [ -n "$RABBITMQ_HOST" ]; then
  /app/wait-for-it.sh "$RABBITMQ_HOST:${RABBITMQ_PORT}" --timeout=30 --strict -- \
    echo "RabbitMQ service is up"
fi

# Run the main container command.
exec "$@"