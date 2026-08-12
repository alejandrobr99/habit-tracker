#!/bin/sh

set -eu

app_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$app_root/backend"
"$app_root/backend/venv/bin/alembic" upgrade head
"$app_root/backend/venv/bin/python" -m app.bootstrap
# The application derives the client address from X-Forwarded-For using
# PLANNER_TRUSTED_PROXY_HOPS. Trusting proxy headers from any peer here would let a
# caller choose its own address and reset every per-address limit.
exec "$app_root/backend/venv/bin/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "127.0.0.1"
