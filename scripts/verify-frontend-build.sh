#!/bin/sh

# The Content-Security-Policy in specs/006-security-hardening.md allows no inline
# script or style. If the build ever emits either, the application breaks in
# production only, so this check fails the build instead.

set -eu

entry=${1:-frontend/dist/index.html}

if [ ! -f "$entry" ]; then
    echo "No se encontró el build en $entry. Ejecuta make build primero."
    exit 1
fi

if grep -q '<style' "$entry"; then
    echo "El build emite estilo en línea y la política de contenido lo bloquearía."
    exit 1
fi

if grep -oE '<script[^>]*>' "$entry" | grep -qv 'src='; then
    echo "El build emite script en línea y la política de contenido lo bloquearía."
    exit 1
fi

echo "El build no emite script ni estilo en línea."
