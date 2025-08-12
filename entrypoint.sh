#!/bin/bash
export POSTGRES_PASSWORD=$(cat /run/secrets/pg_password)
export DATABASE_URL="postgresql://postgres:$POSTGRES_PASSWORD@postgres_db:5432/crm_db"

exec "$@"
