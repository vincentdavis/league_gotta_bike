#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Install production dependencies
echo "Installing production dependencies..."
uv sync --frozen

# Install Tailwind CSS dependencies and build
echo "Installing Tailwind CSS dependencies..."
uv run manage.py tailwind install

echo "Building Tailwind CSS for production..."
uv run manage.py tailwind build

# Run Django migrations.
echo "Running migrations..."
uv run manage.py migrate

# Collect static files.
echo "Collecting static files..."
uv run manage.py collectstatic --noinput

# EnsureSuperuser
echo "Ensuring Superuser..."
uv run manage.py ensure_superuser

# Start the db_worker in the background
echo "Starting db_worker..."
uv run manage.py db_worker &

# Start the server with Daphne (ASGI server for WebSocket support)
echo "Starting Daphne server..."
uv run daphne -b 0.0.0.0 -p "${PORT:-8000}" league_gotta_bike.asgi:application