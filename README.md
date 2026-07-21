# El Bisne Backend

Backend de El Bisne construido con FastAPI, PostgreSQL, SQLAlchemy asíncrono,
Alembic y `uv`. El proyecto está dockerizado: Docker Compose levanta la API y
PostgreSQL, espera a que la base de datos esté lista y aplica las migraciones
antes de iniciar FastAPI.

## Tecnologías

- Python 3.12
- FastAPI
- PostgreSQL 17
- SQLAlchemy 2 con `asyncpg`
- Alembic
- `uv` para dependencias y entorno virtual
- Docker y Docker Compose

## Estructura

```text
app/
├── api/             # Rutas HTTP
├── core/            # Configuración de la aplicación
├── db/              # Base declarativa y sesión de SQLAlchemy
└── main.py          # Aplicación FastAPI
migrations/          # Entorno y versiones de Alembic
tests/               # Pruebas automatizadas
compose.yaml         # API + PostgreSQL
Dockerfile           # Imagen de la API
pyproject.toml       # Proyecto y dependencias de uv
```

## Inicio rápido con Docker

Requisitos: Docker Engine y Docker Compose v2.

```bash
cd El-Bisne-Backend
cp .env.example .env
```

Antes de desplegar, cambia `POSTGRES_PASSWORD` en `.env`. Como
`DATABASE_URL` se usa al ejecutar comandos desde la máquina anfitriona, debe
contener la misma contraseña:

```dotenv
POSTGRES_PASSWORD=una-clave-segura
DATABASE_URL=postgresql+asyncpg://el_bisne:una-clave-segura@localhost:5432/el_bisne
```

Construye y levanta todo:

```bash
docker compose up --build
```

En segundo plano:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

Servicios disponibles:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/v1/health>
- PostgreSQL: `localhost:5432`

El servicio `api` ejecuta `alembic upgrade head` automáticamente en cada
arranque. Las migraciones ya aplicadas no se repiten.

Para detener los contenedores conservando los datos:

```bash
docker compose down
```

Para borrar también el volumen de PostgreSQL y todos sus datos:

```bash
docker compose down -v
```

> `down -v` es destructivo: elimina la base de datos local del proyecto.

## Desarrollo local con `uv`

Puede ejecutarse FastAPI en la máquina y mantener únicamente PostgreSQL en
Docker:

```bash
cp .env.example .env
docker compose up -d db
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

En este modo `DATABASE_URL` usa `localhost`. Dentro de Docker Compose la API
recibe automáticamente una URL equivalente cuyo host es `db`, el nombre del
servicio de PostgreSQL.

## Migraciones

Después de crear o modificar modelos de SQLAlchemy, impórtalos desde
`migrations/env.py` para que formen parte de `Base.metadata`. Luego genera y
revisa la migración:

```bash
uv run alembic revision --autogenerate -m "crear tabla de productos"
uv run alembic upgrade head
```

Para consultar o aplicar migraciones dentro del contenedor:

```bash
docker compose exec api uv run --no-sync alembic current
docker compose exec api uv run --no-sync alembic upgrade head
```

Genera las migraciones desde la máquina anfitriona para que los nuevos archivos
queden guardados en `migrations/versions/` y puedan confirmarse en Git.

Comandos adicionales:

```bash
uv run alembic current
uv run alembic history
uv run alembic downgrade -1
```

## Dependencias, pruebas y calidad

```bash
# Dependencia de producción
uv add nombre-del-paquete

# Dependencia de desarrollo
uv add --dev nombre-del-paquete

# Validaciones
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Después de cambiar dependencias, confirma tanto `pyproject.toml` como
`uv.lock`, y reconstruye la imagen:

```bash
docker compose build api
```

## Variables de entorno

| Variable | Uso | Valor de ejemplo |
|---|---|---|
| `APP_NAME` | Nombre mostrado por FastAPI | `El Bisne API` |
| `APP_ENV` | Entorno de ejecución | `development` |
| `POSTGRES_DB` | Base creada por PostgreSQL | `el_bisne` |
| `POSTGRES_USER` | Usuario de PostgreSQL | `el_bisne` |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `change-me` |
| `POSTGRES_PORT` | Puerto publicado en el host | `5432` |
| `DATABASE_URL` | URL asíncrona para ejecución local | `postgresql+asyncpg://...` |

El archivo `.env` está ignorado por Git. No almacenes credenciales reales en
`.env.example` ni en el repositorio.

## Publicar en GitHub

Este checkout ya tiene configurado el remoto
`git@github.com:Tecnologias-Orbita/El-Bisne-Backend.git`:

```bash
git add .
git commit -m "feat: dockerize API with PostgreSQL"
git push -u origin main
```

Para un repositorio nuevo sin remoto:

```bash
git init -b main
git add .
git commit -m "feat: initialize FastAPI backend"
gh auth login
gh repo create El-Bisne-Backend --private --source=. --remote=origin --push
```
