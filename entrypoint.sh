#!/bin/sh

set -e

echo "Entrypoint: Database (db_teams) is reported as healthy. Running migrations for teams_service..."

alembic upgrade head

echo "Entrypoint: Migrations finished. Starting application (Uvicorn)..."

exec "$@"