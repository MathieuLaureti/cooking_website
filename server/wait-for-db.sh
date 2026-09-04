#!/bin/sh
set -e

echo "Waiting for Postgres at $DB_HOST:$DB_PORT..."

while true; do
  set +e
  python -u - << END
import os
import sys

import psycopg

try:
    conn = psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=3,
    )
    conn.close()
    sys.exit(0)
except psycopg.OperationalError as e:
    message = str(e).lower()
    print("Connection failed:", e, flush=True)
    if "password authentication failed" in message or "role" in message and "does not exist" in message:
        sys.exit(2)
    sys.exit(1)
except Exception as e:
    print("Connection failed:", e, flush=True)
    sys.exit(1)
END
  status=$?
  set -e

  if [ "$status" -eq 0 ]; then
    break
  fi
  if [ "$status" -eq 2 ]; then
    echo "Fatal database authentication error — check DB_USER and DB_PASSWORD in .env"
    exit 1
  fi
  echo "$DB_HOST:$DB_PORT - no response"
  sleep 2
done

echo "Postgres connection test successful"
echo "Running migrations..."
alembic upgrade head
echo "Starting server..."
exec "$@"
