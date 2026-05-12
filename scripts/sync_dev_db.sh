#!/usr/bin/env bash
# Copy colandr to colandr_dev. Needs psql and pg_dump; colandr_dev must already exist.
# Use whatever connection you use for normal psql (env, .pgpass, etc.); no settings here.
set -euo pipefail

export PGSERVICE=colandr

if ! psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'colandr'" | grep -q 1; then
  echo "Database colandr not found." >&2
  exit 1
fi
if ! psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'colandr_dev'" | grep -q 1; then
  echo "Database colandr_dev not found (create it first)." >&2
  exit 1
fi

echo "Copying colandr -> colandr_dev ..."
pg_dump colandr | psql -d colandr_dev -v ON_ERROR_STOP=1

echo "Done."
