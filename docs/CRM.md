# CRM interno

Se implementan modelos, esquemas, repositorios, servicios, migraciones y rutas HTTP del CRM. Las rutas y la autenticación existentes permanecen disponibles. La capa HTTP obtiene `actor` con `get_current_active_user` mediante la dependencia `ActiveUser` y llama a los servicios. Los repositorios y servicios comparten la sesión asíncrona de `get_async_db` a través de las dependencias de FastAPI.

## Archivos

| Capa | Archivos |
| --- | --- |
| Modelos nuevos | `app/models/{customer,contact,service,interaction,appointment,ticket,ticket_comment}.py`, `crm_base.py`, `crm_enums.py` |
| Esquemas nuevos | Los siete módulos equivalentes en `app/schemas/`, más `crm_base.py`; cada entidad tiene `Create`, `Update`, `Response` y `Filters` |
| Repositorios nuevos | Los siete módulos equivalentes en `app/repositories/`, más `crm_repository.py` |
| Servicios nuevos | `app/services/{customer,contact,service_catalog,interaction,appointment,ticket,ticket_comment}.py`, `crm_base.py` |
| API | `app/api/dependencies.py`, siete routers en `app/api/routes/{customers,contacts,services,interactions,appointments,tickets,ticket_comments}.py`, registrados en `app/main.py` |
| Migración | `migrations/versions/c7a1e4b92063_add_crm_core.py` |
| Verificación | `test/unit/test_crm_schemas.py`, `test/integration/test_crm.py`, `test/integration/test_crm_routes.py`, `scripts/verify_crm_migration.py` |
| Archivos adaptados | Registro de modelos, relaciones inversas en `User`, consulta de usuarios por UUID, conflicto al eliminar usuarios referenciados, fixtures y expectativas de pruebas, README y `.gitignore` |

`Service` es el modelo del catálogo; `ServiceCatalogService` implementa su lógica de negocio.

## Endpoints

Todos requieren `Authorization: Bearer <access_token>` de un usuario activo. Bajo `/api/v1`, cada recurso expone `POST /recurso` (201), `GET /recurso` (lista paginada), `GET /recurso/{id}` y `PATCH /recurso/{id}` (200).

| Recurso | Ruta | Identificador |
| --- | --- | --- |
| Clientes | `/customers` | `customer_id` |
| Contactos | `/contacts` | `contact_id` |
| Catálogo | `/services` | `service_id` |
| Interacciones | `/interactions` | `interaction_id` |
| Citas | `/appointments` | `appointment_id` |
| Tickets | `/tickets` | `ticket_id` |
| Comentarios | `/ticket-comments` | `comment_id` |

Acciones adicionales (POST, respuesta 200 con el registro actualizado):

- `/customers/{customer_id}/archive`
- `/contacts/{contact_id}/deactivate`
- `/services/{service_id}/deactivate`

No hay eliminación física del CRM. Para reactivar un cliente usa PATCH con `status=ACTIVE`; para un contacto o servicio, `is_active=true`. Los cambios de estado de ticket se envían mediante PATCH.

Los filtros de los esquemas `Filters` se reciben como query parameters, no como cuerpo GET. Por ejemplo, `GET /api/v1/tickets?customer_id=<uuid>&status=OPEN&priority=HIGH&limit=20&offset=0` y `GET /api/v1/ticket-comments?ticket_id=<uuid>`. Crear un comentario requiere `ticket_id`, `body` y opcionalmente `is_internal` en el JSON; el autor procede del token.

`/docs` y `/openapi.json` describen cuerpos, respuestas, filtros y autenticación. Los UUID y filtros inválidos devuelven 422, los recursos ausentes o ajenos 404, las operaciones reservadas al administrador 403 y los conflictos de negocio 409. La ausencia de token devuelve 401 y las cuentas inactivas conservan el 400 de la dependencia existente.

## Relaciones e historial

- `Customer` tiene contactos, interacciones, citas y tickets. Su creador y responsable referencian a `User` por separado.
- `Contact` pertenece a un cliente y puede referenciarse desde interacciones, citas y tickets.
- `Service` puede asociarse con muchos tickets. `Ticket` tiene muchos `TicketComment`.
- Creadores, autores y responsables referencian al usuario existente. Todas las relaciones usan `back_populates`; las referencias múltiples a usuarios declaran `foreign_keys`.
- Todas las claves foráneas nuevas usan `ON DELETE RESTRICT`. El ORM usa `passive_deletes="all"`, sin cascadas de eliminación. El borrado físico de registros referenciados falla, incluso con relaciones cargadas. El usuario puede desactivarse mediante la administración existente; intentar borrar un usuario con historial devuelve 409.
- Los clientes se archivan con `status=INACTIVE`; servicios y contactos con `is_active=False`. No se ofrecen métodos de eliminación del historial. Se pueden reactivar mediante actualización.
- Un cliente archivado conserva consultas y modificaciones de recursos existentes, incluidos nuevos comentarios sobre tickets existentes. Para crear contactos, interacciones, citas o tickets nuevos se debe reactivar al cliente.
- `customer_id` y `ticket_id` son inmutables en las actualizaciones: no se trasladan contactos ni historial a otro cliente/ticket. Se valida la pertenencia del contacto tanto al crear como al actualizar.

## Autorización y validaciones

`ADMIN` activo gestiona todos los recursos. `USER` activo accede únicamente a clientes asignados a él y a sus recursos. Crear un cliente como `USER` fuerza su propia asignación; solo `ADMIN` puede reasignarlo, incluso a `null`. Asignar una cita o ticket a otro empleado **no concede acceso** a ese empleado si no es responsable del cliente. Reasignar el cliente cambia el acceso a todo su historial.

El catálogo es consultable por todos los usuarios activos y administrable solo por `ADMIN`. Los listados pueden incluir registros desactivados para consultar historial y permiten filtrarlos explícitamente. `is_internal` describe el comentario; esta fase solo tiene empleados, sin acceso de clientes externos.

Los servicios aplican el alcance de acceso en SQL antes de obtener un registro y antes de contar/paginar. UUID inexistentes o fuera de alcance devuelven 404. Los comentarios se consultan mediante un join a ticket y cliente; crear o listar por ticket valida primero el acceso al ticket.

Los responsables deben existir y estar activos al asignarse. Las nuevas asociaciones requieren contactos y servicios activos; desactivar uno no invalida asociaciones históricas. Los autores/creadores provienen exclusivamente de `actor.id`.

Los textos se recortan y validan: nombres y asuntos hasta 255 caracteres, contenido hasta 20 000, identificador fiscal 64, teléfono 50, categoría 100, ubicación 500 y URL 2048. Se validan correos y URLs HTTP/HTTPS. No se impone unicidad comercial a nombres o identificadores fiscales sin una regla de negocio explícita.

Las entradas rechazan campos desconocidos, fechas sin zona y `null` en campos obligatorios. Los PATCH usan `model_dump(exclude_unset=True)`: omitir conserva el valor; `null` limpia únicamente campos opcionales; `False` se conserva. Las fechas de entrada se normalizan a UTC; PostgreSQL almacena `TIMESTAMP WITH TIME ZONE`. La cita se valida sobre el intervalo resultante completo y tiene el CHECK `ends_at > starts_at`.

Los repositorios son la única capa que confirma las mutaciones (`commit`, `refresh`, `rollback`), siguiendo `UserRepository`. Los servicios validan y autorizan antes de persistir. Una mutación corresponde a una transacción; no deben componerse varias llamadas de escritura suponiendo atomicidad conjunta.

Los conflictos de integridad conocidos se distinguen por SQLSTATE (unicidad, clave foránea, CHECK o NOT NULL). Los demás errores de base de datos se propagan al manejo existente y no se presentan como duplicados.

## Estados de tickets

Los tickets nacen en `OPEN`; el cliente de la API no controla `resolved_at` ni `closed_at`.

| Estado actual | Siguientes estados permitidos |
| --- | --- |
| OPEN | IN_PROGRESS, WAITING_CUSTOMER, RESOLVED |
| IN_PROGRESS | WAITING_CUSTOMER, RESOLVED |
| WAITING_CUSTOMER | IN_PROGRESS, RESOLVED |
| RESOLVED | CLOSED, OPEN |
| CLOSED | OPEN |

Repetir el estado actual es idempotente. Resolver establece `resolved_at`; cerrar conserva esa fecha y establece `closed_at`; reabrir a `OPEN` limpia ambas. No se permite cerrar sin resolver. Un CHECK adicional protege la coherencia entre estados y fechas.

## Consultas y uso de servicios

Cada servicio recibe su repositorio y cada operación pública recibe el usuario autenticado:

```python
from app.repositories.ticket import TicketRepository
from app.schemas.ticket import TicketFilters, TicketUpdate
from app.services.ticket import TicketService

service = TicketService(TicketRepository(db))
page = await service.get_all(TicketFilters(status="OPEN", limit=20), actor)
ticket = await service.update(ticket_id, TicketUpdate(priority="HIGH"), actor)
```

Los filtros incluyen, según entidad, cliente, contacto, servicio, responsable, estado, prioridad, actividad, canal y fechas. Las fechas de filtro son inclusivas. La búsqueda textual es una subcadena literal; `%` y `_` se escapan. El orden es `created_at DESC, id DESC`, con `offset`, límite inicial 20 y máximo 100. El total corresponde al mismo alcance y filtros.

Las respuestas contienen campos escalares y UUID, sin colecciones anidadas. No requieren carga de relaciones durante serialización. Todas las relaciones tienen `lazy="raise"`; quien necesite navegar relaciones debe cargarlas explícitamente con `selectinload`, como muestran las pruebas.

## Migraciones

La revisión nueva parte de `9f2a3c6d8e41`; el único head es `c7a1e4b92063`. Se generó con autogenerate contra PostgreSQL 16 y se revisó manualmente. Añade siete tablas y seis enums propios `crm_*`; no altera `users`, `refresh_token` ni `user_role_enum`. El downgrade elimina solo los objetos del CRM, en orden inverso de dependencias. Los tipos se crean explícitamente con `checkfirst=True`, y las columnas usan `create_type=False` para evitar creación duplicada.

Desde PowerShell, en la raíz del repositorio:

```powershell
docker compose up -d postgres redis
docker compose build api
docker compose --profile tools run --rm migrate heads
docker compose --profile tools run --rm migrate upgrade head
docker compose --profile tools run --rm migrate check
docker compose --profile tools run --rm migrate current
```

Para ejecutar la API actualizada después de migrar:

```powershell
docker compose up -d api
```

El downgrade hasta `9f2a3c6d8e41` conserva autenticación y usuarios, pero elimina las tablas y datos del CRM; el verificador siguiente lo ejecuta únicamente en una base desechable.

## Pruebas reproducibles

Con un entorno Python 3.12 funcional:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m scripts.verify_crm_migration
```

El último comando usa el servidor PostgreSQL configurado y exige permiso `CREATEDB`. Crea una base `crm_verify_<uuid>`, verifica upgrade/downgrade/upgrade, enums, restricciones y conservación exacta de filas de usuario/token; después ejecuta la integración del CRM contra PostgreSQL y elimina esa base. Nunca migra la base de la aplicación. Las pruebas normales usan SQLite en memoria. `create_all()` solo se usa para ese fixture SQLite; PostgreSQL usa exclusivamente Alembic.

Alternativa Docker usando la imagen `api` y las versiones de prueba declaradas en `requirements-dev.txt`:

```powershell
docker compose run --rm --no-deps --entrypoint sh -v .:/workspace -w /workspace -e PYTHONPATH=/tmp/test-deps:/install/lib/python3.12/site-packages:/workspace -e DEBUG=false api -c 'pip install --target /tmp/test-deps pytest==9.1.1 pytest-asyncio==1.4.0 httpx==0.28.1 aiosqlite==0.22.1 && python -m pytest -q && python -m scripts.verify_crm_migration'
```

Este comando instala solo herramientas de prueba en `/tmp` del contenedor efímero y reutiliza las dependencias de aplicación ya instaladas por el Dockerfile. Requiere `postgres` iniciado y acceso al índice de paquetes. No inicia Uvicorn ni ejecuta el entrypoint que migra la base de la aplicación.

## Resultado de la verificación

Verificado en la imagen Docker del proyecto con SQLAlchemy 2.0.52, Pydantic 2.13.5, FastAPI 0.141.1 y Alembic 1.19.1:

- Suite completa con los endpoints: **245 pruebas aprobadas**.
- Integración del CRM y sus rutas HTTP sobre PostgreSQL 16: **80 pruebas aprobadas** adicionales.
- Upgrade, downgrade y segundo upgrade correctos; un único head; `alembic check` sin diferencias.
- Usuarios, refresh tokens y enum de roles conservados en ambas direcciones.
- Revisión estática de los archivos Python cambiados y `git diff --check` sin errores.

La migración se aplicó únicamente en bases temporales, eliminadas al terminar. Queda pendiente aplicarla en la base de la aplicación con los comandos anteriores. No se modificó `.env`. Cuatro expectativas antiguas de pruebas se ajustaron a las rutas y mensajes de autenticación existentes, sin cambiar esos endpoints.
