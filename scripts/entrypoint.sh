#!/bin/sh
set -e

DB_FILE="${DB_PATH:-/app/db/kazmedsim.db}"
SCHEMA_FILE="${SCHEMA_PATH:-/app/schema.sql}"
mkdir -p "$(dirname "$DB_FILE")"

if [ ! -f "$DB_FILE" ]; then
  echo "→ DB not found at $DB_FILE — initializing schema and seeding..."
  python -c "import sqlite3; conn = sqlite3.connect('$DB_FILE'); conn.executescript(open('$SCHEMA_FILE').read()); conn.commit(); conn.close()"
  python scripts/seed_db.py
  python scripts/seed_scenarios_v2.py
  echo "→ Seed complete."
else
  echo "→ DB exists at $DB_FILE — skipping seed."
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
