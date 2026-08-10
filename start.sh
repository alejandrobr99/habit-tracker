#!/bin/sh

set -eu

app_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$app_root/backend"
"$app_root/backend/venv/bin/alembic" upgrade head
exec "$app_root/backend/venv/bin/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
