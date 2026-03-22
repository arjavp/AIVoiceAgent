#!/bin/bash
set -e

# Wait for DB
echo "Waiting for PostgreSQL at $DJANGO_DATABASE_HOST..."
if [ -n "$DJANGO_DATABASE_HOST" ]; then
    while ! pg_isready -h "$DJANGO_DATABASE_HOST" -p "${DJANGO_DATABASE_PORT:-5432}" > /dev/null 2>&1; do
      echo "PostgreSQL is unavailable - sleeping"
      sleep 2
    done
    echo "PostgreSQL is up!"
fi

if [ "$1" = 'web' ]; then
    echo "Enabling pgvector extension..."
    export PGPASSWORD=${DJANGO_DATABASE_PASSWORD:-postgres}
    psql -h "$DJANGO_DATABASE_HOST" -U "${DJANGO_DATABASE_USER:-postgres}" -d "${DJANGO_DATABASE_NAME:-voice_agent}" -c "CREATE EXTENSION IF NOT EXISTS vector;" || true
    echo "Running migrations..."
    python config/manage.py migrate --noinput
    echo "Starting Web Server..."
    exec python config/manage.py runserver 0.0.0.0:8000
elif [ "$1" = 'worker' ]; then
    echo "Starting Celery Worker..."
    cd config && exec celery -A config worker --loglevel=info
elif [ "$1" = 'agent' ]; then
    echo "Starting LiveKit Agent..."
    # 'start' command for production worker mode
    exec python agent.py start
else
    # Execute any other command passed
    exec "$@"
fi
