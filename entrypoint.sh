#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate

echo "Creating MinIO bucket..."
python manage.py create_minio_bucket || echo "Bucket creation failed (maybe already exists)"

echo "Starting server..."
exec python manage.py runserver 0.0.0.0:8000