#!/bin/sh
# Entrypoint for the Django container: apply migrations, collect static files,
# then hand off to the CMD (gunicorn) passed as arguments.
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"
