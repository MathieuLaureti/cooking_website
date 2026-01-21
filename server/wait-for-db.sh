#!/bin/sh
set -e

echo "Waiting for Postgres at $DB_HOST:$DB_PORT..."

until python -u - << END
import psycopg, os, sys
try:
    conn = psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=6667,
        connect_timeout=3,  # <-- important
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    print("Connection failed:", e, flush=True)
    sys.exit(1)
END
do
  echo "$DB_HOST:$DB_PORT - no response"
  sleep 2
done

echo "Postgres connection test successful"
exec "$@"
