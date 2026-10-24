# Jireh CRM API

Copia independiente de la API de JobList que conserva autenticación, usuarios, administración e infraestructura compartida, y excluye completamente jobs y skills. El código conservado se reutiliza del proyecto fuente; los cambios se limitan a retirar referencias excluidas y preparar esta copia para una base de datos propia.

## Requisitos

- Python 3.12
- PostgreSQL (para ejecución local) y Redis (opcional; sin `REDIS_URL`, SlowAPI usa almacenamiento en memoria)
- Docker Desktop con Docker Compose, para ejecutar los servicios en contenedores

## Configuración local

Desde PowerShell, en la raíz del proyecto:

```powershell
Copy-Item .env.example .env
```

Edita `.env`: reemplaza `DB_PASSWORD` y `JWT_SECRET_KEY` por valores locales propios. La clave JWT debe tener al menos 32 caracteres. No uses credenciales ni conexiones del proyecto original. Para desarrollo local, configura PostgreSQL en `localhost:5433` y Redis en `localhost:6379`, o ajusta los hosts y puertos para tus servicios.

## Instalación

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Migraciones

La copia incluye una migración inicial nueva, independiente del historial del proyecto original. Crea únicamente `users`, `refresh_token` y `alembic_version`.

Con PostgreSQL configurado en `.env`:

```powershell
alembic upgrade head
alembic current
```

La aplicación usa PostgreSQL asíncrono con `asyncpg`; Alembic utiliza `psycopg2` para las migraciones.

## Ejecución local

```powershell
uvicorn app.main:app --reload
```

La API escucha en `http://127.0.0.1:8000`; la documentación OpenAPI está en `/docs` y `/redoc`. Los endpoints están bajo `/api/v1`: autenticación (`/auth`), perfil y usuarios (`/users`), administración (`/admin`) y health checks (`/health`, `/health/ready`).

## Docker Compose

Desarrollo:

```powershell
Copy-Item .env.example .env
# Edita .env y sustituye los valores de ejemplo antes de continuar.
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs --tail 100 api
```

El servicio `api` ejecuta `alembic upgrade head` antes de iniciar Uvicorn. PostgreSQL, Redis y sus volúmenes tienen nombres propios de esta copia, distintos de los del proyecto original.

Para detener los servicios conservando los datos:

```powershell
docker compose down
```

Producción requiere preparar `.env.production` por separado con las variables de `.env.example`, usando secretos seguros y valores de producción. No se incluye ese archivo ni credenciales reales:

```powershell
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

## Pruebas

Las pruebas configuran sus propias variables de entorno y usan SQLite en memoria; no se conectan a la base de datos configurada en `.env` ni reutilizan volúmenes Docker.

```powershell
python -m pytest -q
python -m pytest test/unit/routes -q
python -m pytest test/integration -q
python -m pytest test/test_logging.py test/unit/test_migration_config.py -q
```

El script `scripts/security_probes.py` contiene pruebas históricas que afirman comportamientos vulnerables observados y no forma parte de la suite de liberación:

```powershell
python -m pytest scripts/security_probes.py -q
```

## Variables de entorno

`.env.example` enumera los nombres utilizados por la configuración de la aplicación. Conserva los nombres originales, incluido `ENVIROMENT`. Los valores que empiezan por `REPLACE_WITH_` son marcadores y deben cambiarse antes de ejecutar servicios.
