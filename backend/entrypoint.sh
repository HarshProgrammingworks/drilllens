#!/bin/sh
set -e
echo "Waiting for database migrations..."
alembic upgrade head
python /scripts/seed_database.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
