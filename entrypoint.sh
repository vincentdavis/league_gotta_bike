#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Run Django migrations.
echo "Running migrations..."
uv run manage.py migrate

# EnsureSuperuser
echo "Ensuring Superuser..."
uv run manage.py ensure_superuser

# Start the db_worker in the background
echo "Starting db_worker..."
uv run manage.py db_worker &

# Start the server with Daphne (ASGI server for WebSocket support)
echo "Starting Daphne server..."
uv run daphne -b 0.0.0.0 -p "${PORT:-8000}" league_gotta_bike.asgi:application