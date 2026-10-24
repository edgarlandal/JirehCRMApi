# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install --no-warn-script-location -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages:/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados desde la etapa builder
COPY --from=builder /install /install

# Crear usuario no-root por seguridad
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

COPY . .
# 1. Asegurar que estamos trabajando como root (comportamiento por defecto)
USER root

# 2. Copiar todo el código o la carpeta scripts
COPY . /app

# 3. Dar permisos de ejecución e indicar propiedad de los archivos a appuser
RUN sed -i 's/\r$//' /app/scripts/entrypoint.sh && \
    chmod +x /app/scripts/entrypoint.sh && \
    chown -R appuser:appgroup /app

# 4. Cambiar al usuario no privilegiado justo antes de ejecutar la app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
