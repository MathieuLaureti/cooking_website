#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Waiting for timescale:6667..."

while ! timeout 1s bash -c "cat < /dev/null > /dev/tcp/timescale/6667" 2>/dev/null; do
  echo "Database at timescale:6667 is unavailable - sleeping"
  sleep 1
done

echo "Running migrations..."
# Adjust this command based on your migration tool (Alembic example)
alembic upgrade head

echo "Starting server..."
exec "$@"
