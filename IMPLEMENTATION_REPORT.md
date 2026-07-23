# Informe de implementación de El Bisne Backend

## Resumen ejecutivo

Se implementó la base de un backend modular para El Bisne utilizando FastAPI,
PostgreSQL, SQLAlchemy asíncrono, Alembic y CQRS lógico.

El sistema ya cuenta con infraestructura CQRS, Unit of Work, autenticación,
multi-tenancy, landing, formularios, catálogo, pedidos invitados, transactional
outbox y analítica básica. La aplicación carga 21 tablas y expone 18 rutas en
OpenAPI.

La solución constituye una base funcional del MVP, pero todavía requiere
completar varios flujos, ejecutar pruebas reales con PostgreSQL y fortalecer la
seguridad antes de considerarla lista para producción.

## Trabajo realizado

### 1. Arquitectura modular

El backend se organizó por dominios:

- Autenticación.
- Negocios.
- Sitios y landing.
- Formularios.
- Catálogo.
- Pedidos.
- Notificaciones.
- Analítica.

Cada dominio sigue, en términos generales, esta división:

```text
api/
application/
domain/
infrastructure/
```

El flujo principal es:

```text
Route → Command/Query Bus → Handler → Service → Repository → PostgreSQL
```

Las rutas implementadas no acceden directamente a SQLAlchemy ni contienen las
reglas centrales del negocio.

La descripción completa se encuentra en `BACKEND_PLAN.md`.

### 2. Infraestructura CQRS

Se implementaron:

- `CommandBus` para operaciones que modifican estado.
- `QueryBus` para lecturas.
- Registro explícito de handlers.
- Error controlado para mensajes sin handler.
- `UnitOfWork` sobre sesiones asíncronas de SQLAlchemy.
- Commit al completar commands.
- Rollback ante excepciones.
- Sesiones de lectura sin commit para queries.
- Manejo global de errores de aplicación.

CQRS es lógico: commands y queries están separados en código, pero comparten la
misma base de datos PostgreSQL.

### 3. Autenticación

Se añadieron:

- Registro con email y contraseña.
- Login.
- Tokens JWT de acceso.
- Refresh tokens rotativos almacenados como hash.
- Consulta del usuario autenticado.
- Contraseñas protegidas con PBKDF2-HMAC-SHA256.
- Estados de usuario activo, verificado, archivado y administrador global a
  nivel del modelo.

Endpoints principales:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
```

### 4. Negocios y multi-tenancy

Se implementó:

- Creación de negocios.
- Slug público único y normalizado.
- Asociación automática del creador como `owner`.
- Relación muchos-a-muchos entre usuarios y negocios.
- Roles `owner`, `admin`, `editor` y `viewer`.
- Listado de negocios administrados por el usuario.
- Verificación de pertenencia antes de administrar recursos.
- Creación automática del sitio base del negocio.

### 5. Landing

Se añadieron modelos y casos de uso para:

- Sitios asociados a negocios.
- Plantillas.
- Configuración de paleta, tipografía y SEO.
- Secciones ordenadas y tipadas:
  - `hero`.
  - `text`.
  - `gallery`.
  - `contact`.
  - `form`.
- Publicación de la landing.
- Consulta pública por slug.

### 6. Formularios

Se implementó:

- Creación de formularios.
- Campos configurables y ordenados.
- Tipos básicos de campo.
- Campos obligatorios.
- Validación de campos desconocidos y faltantes.
- Envío público de respuestas.
- Creación de eventos outbox al recibir solicitudes.

### 7. Catálogo

Se añadieron modelos para:

- Categorías.
- Productos y servicios.
- Imágenes externas.
- Productos relacionados.
- Ofertas con vigencia.
- Disponibilidad.
- Publicación.
- Inventario opcional.
- Archivado.

Casos de uso conectados:

- Crear categorías.
- Crear productos o servicios.
- Consultar el catálogo público de un negocio.

Los precios usan `Decimal` y PostgreSQL `NUMERIC(14, 2)`.

### 8. Pedidos

Se implementó:

- Pedidos realizados por invitados.
- Contacto mediante email o teléfono.
- Cabecera obligatoria `Idempotency-Key`.
- Prevención básica de pedidos duplicados.
- Verificación de productos disponibles.
- Cálculo de subtotal y total.
- Snapshot del nombre y precio del producto.
- Historial inicial del estado.
- Estados contemplados:
  - `pending`.
  - `confirmed`.
  - `in_progress`.
  - `completed`.
  - `cancelled`.
- Registro de un evento analítico.
- Registro de un evento outbox en la misma transacción.

### 9. Outbox y analítica

Se crearon modelos para:

- Eventos outbox.
- Intentos y errores de procesamiento.
- Entregas de notificaciones.
- Eventos analíticos anónimos.

También se implementó:

- Registro público de visitas y vistas de productos.
- Dashboard básico por negocio.
- Cantidad de visitas.
- Vistas de productos.
- Total de pedidos.
- Pedidos completados.
- Tasa de conversión.

### 10. Base de datos

El modelo actual carga 21 tablas PostgreSQL.

Se añadió una migración inicial en:

```text
migrations/versions/20260721_0001_initial_schema.py
```

Alembic carga todos los modelos mediante:

```text
app/db/models.py
```

### 11. Documentación y configuración

Se actualizaron:

- `README.md` con arquitectura y endpoints.
- `.env.example` con variables JWT y PostgreSQL.
- Docker Compose para pasar `SECRET_KEY`.
- Configuración de pytest.
- Documentación OpenAPI automática.
- `BACKEND_PLAN.md` con el diseño arquitectónico y la evolución propuesta.

### 12. Pruebas y validaciones

Se añadieron pruebas para:

- Registro y resolución de handlers CQRS.
- Error ante mensajes sin handler.
- Cálculo monetario de pedidos.
- Rechazo de productos inexistentes.
- Regla arquitectónica que impide importar SQLAlchemy desde las rutas.
- Health check.

Resultados obtenidos:

```text
6 pruebas aprobadas
Ruff aprobado
Formato aprobado
21 tablas SQLAlchemy cargadas
18 rutas OpenAPI generadas
git diff --check aprobado
```

No se ejecutaron Docker, PostgreSQL ni migraciones reales, respetando la
indicación de no realizar construcciones o descargas con una conexión limitada.

## Trabajo pendiente

### Prioridad alta

#### 1. Probar contra PostgreSQL real

Falta comprobar:

- Aplicación real de la migración.
- Constraints y claves foráneas.
- Commit y rollback.
- Idempotencia bajo peticiones concurrentes.
- Aislamiento multi-tenant.
- Consultas y tipos JSONB.
- UUID, zonas horarias y `NUMERIC`.

Cuando exista una conexión estable:

```bash
docker compose up -d db
uv run alembic upgrade head
uv run pytest
```

#### 2. Mejorar la migración inicial

La migración inicial utiliza `Base.metadata.create_all()`. Es suficiente como
punto de partida, pero debe reemplazarse por operaciones Alembic explícitas:

```python
op.create_table(...)
op.create_index(...)
op.create_unique_constraint(...)
```

Esto permitirá revisar el SQL, controlar los downgrades y mantener un historial
de producción más seguro.

#### 3. Completar permisos por rol

Falta definir y aplicar una matriz fina:

- `owner`: control total.
- `admin`: miembros, contenido y pedidos.
- `editor`: contenido y catálogo.
- `viewer`: solo lectura.

También faltan:

- Invitar miembros.
- Aceptar invitaciones.
- Cambiar roles.
- Eliminar miembros.
- Transferir propiedad.
- Impedir que un negocio quede sin propietario.

#### 4. Completar autenticación

Faltan:

- Verificación de email.
- Recuperación de contraseña.
- Logout y revocación explícita.
- Revocación de todas las sesiones.
- Límite de intentos de login.
- Protección contra fuerza bruta.
- Política de contraseñas.
- Limpieza de refresh tokens expirados.

#### 5. Crear el worker de notificaciones

El outbox almacena eventos, pero aún no existe un proceso que los consuma:

```text
Outbox pendiente
    → Worker toma evento con bloqueo
    → Envía email
    → Registra notification_delivery
    → Marca evento procesado
    → Reintenta con backoff si falla
```

También falta escoger un proveedor como SMTP, Resend, SES o Mailgun.

### Prioridad media

#### 6. Completar CRUD de negocios

Faltan operaciones para:

- Consultar un negocio individual.
- Editar información y contacto.
- Cambiar moneda y zona horaria con reglas seguras.
- Publicar o despublicar.
- Archivar y restaurar.
- Validar los tipos de negocio.

#### 7. Completar landing

Faltan:

- Editar secciones.
- Eliminar o archivar secciones.
- Reordenarlas de forma atómica.
- Ocultarlas.
- Actualizar paleta, tipografía, SEO y favicon.
- Gestionar plantillas.
- Validar el JSONB según cada tipo de bloque.
- Vista previa sin publicar.
- Resolver conflictos de reordenamiento concurrente.

#### 8. Completar formularios

Faltan:

- Listar y consultar formularios.
- Editar y reordenar campos.
- Publicar, despublicar y archivar.
- Listar respuestas en el panel.
- Cambiar el estado de una respuesta.
- Validaciones específicas por tipo de campo.
- Rate limiting y protección antispam.

#### 9. Completar catálogo

Faltan endpoints para:

- Listado administrativo.
- Consulta pública de un producto individual.
- Edición y archivo de categorías.
- Edición, publicación y archivo de productos.
- Disponibilidad e inventario.
- Imágenes adicionales.
- Productos relacionados.
- Creación y desactivación de ofertas.
- Aplicación del precio promocional al pedido.
- Paginación, filtros y búsqueda.
- Reordenamiento.
- Validación de que la categoría pertenece al mismo negocio.

El último punto debe reforzarse antes de exponer el catálogo en producción.

#### 10. Completar administración de pedidos

Faltan:

- Listado paginado.
- Filtros por estado y fecha.
- Detalle administrativo.
- Transiciones de estado controladas.
- Comentarios administrativos.
- Cancelación.
- Matriz de transiciones permitidas.
- Registro del usuario que realiza cada transición.
- Exportación.
- Control de concurrencia.

#### 11. Mejorar idempotencia

Conviene añadir:

- Hash del cuerpo de la petición.
- Rechazo de una clave reutilizada con contenido diferente.
- Manejo explícito de carreras por constraint única.
- Respuesta idéntica en reintentos.
- Política de expiración de claves.

#### 12. Ampliar analítica

Faltan:

- Productos más vistos y solicitados.
- Pedidos por periodo.
- Conversión diaria.
- Fuentes de tráfico.
- Agrupación diaria y mensual.
- Dashboard global de plataforma.
- Acceso exclusivo para administradores globales.
- Prevención de duplicados y bots.
- Retención y limpieza de eventos.
- Política de privacidad.

### Calidad y mantenimiento

#### 13. Reforzar fronteras arquitectónicas

Algunas interfaces de repositorio del dominio todavía importan modelos de
infraestructura. Para conseguir una separación estricta deberían devolver
entidades de dominio o DTOs, no modelos SQLAlchemy.

La dirección deseada es:

```text
domain → no conoce SQLAlchemy
infrastructure → implementa contratos del dominio
application → trabaja con entidades y DTOs
```

También conviene centralizar la autorización multi-tenant en un servicio
dedicado para no repetir comprobaciones en handlers.

#### 14. Añadir más pruebas

Faltan pruebas para:

- Cada handler.
- Unit of Work y rollback.
- Contratos de repositorios.
- PostgreSQL real.
- Autenticación y tokens.
- Permisos por rol.
- Aislamiento entre negocios.
- Landing y formularios.
- Pedidos concurrentes.
- Outbox.
- Analítica.
- Contratos HTTP.
- Upgrade y downgrade de migraciones.

#### 15. Seguridad de producción

Antes de desplegar se debe:

- Exigir una `SECRET_KEY` segura y eliminar el fallback inseguro.
- Configurar CORS por entorno.
- Añadir trusted hosts.
- Incorporar rate limiting.
- Añadir logs estructurados sin información sensible.
- Configurar cabeceras de seguridad.
- Limitar el tamaño de las peticiones.
- Gestionar secretos fuera del repositorio.
- Auditar acciones administrativas.
- Definir una política de datos personales y borrado.

#### 16. Operación y despliegue

Faltan:

- Servicio worker en Docker Compose.
- Readiness y liveness separados.
- Pipeline CI.
- Aplicación automatizada y segura de migraciones.
- Backups de PostgreSQL.
- Métricas y alertas.
- Logs centralizados.
- Configuración diferenciada por entorno.
- Usuario no-root dentro del contenedor.
- Validación del lockfile después de cambios de dependencias.

## Próximo bloque recomendado

El orden recomendado para continuar es:

1. Reemplazar la migración inicial por operaciones Alembic explícitas.
2. Ejecutar pruebas de integración con PostgreSQL.
3. Completar permisos por rol y administración de miembros.
4. Implementar administración de pedidos.
5. Completar CRUD de landing, formularios y catálogo.
6. Implementar el worker de outbox y el envío real de emails.
7. Añadir pruebas de integración y endurecimiento de seguridad.

## Estado general

La base arquitectónica y varios flujos verticales del MVP están implementados.
El proyecto está preparado para continuar por módulos sin colocar lógica en las
rutas, pero todavía no debe considerarse listo para producción.
