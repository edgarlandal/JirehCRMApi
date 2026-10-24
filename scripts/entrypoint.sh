#!/bin/sh
set -e

echo "Esperando y ejecutando migraciones de base de datos..."
alembic upgrade head

echo "Iniciando servidor de aplicación Uvicorn..."
# Cálculo de workers recomendados: (2 * Cores) + 1. Ej. para 2 CPU cores = 4-5 workers
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --proxy-headers \
    --forwarded-allow-ips "*" \
    --no-access-log \
    --timeout-keep-alive 65