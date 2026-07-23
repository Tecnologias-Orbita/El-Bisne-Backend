# Arquitectura de El Bisne Backend

## Objetivo

El Bisne es una plataforma SaaS multi-negocio para publicar landings, catálogos
y formularios, recibir pedidos de invitados y consultar estadísticas. El
backend se implementa como monolito modular con FastAPI, PostgreSQL, SQLAlchemy
asíncrono, Alembic y CQRS lógico.

## Flujo y reglas arquitectónicas

```text
Route → Command/Query Bus → Handler → Service → Repository → PostgreSQL
```

- Las rutas solo traducen HTTP a commands/queries y serializan DTOs.
- Los commands modifican estado y se ejecutan dentro de un `UnitOfWork`.
- Las queries no hacen commit ni modifican estado.
- Los handlers orquestan el caso de uso; las reglas reutilizables viven en
  servicios de aplicación o dominio.
- Cada agregado define su contrato de repositorio y la implementación concreta
  vive en infraestructura.
- Las excepciones de aplicación se convierten a errores HTTP de forma global.
- La sesión, seguridad y buses son dependencias, no variables usadas por rutas.
- El negocio y el evento outbox se guardan en la misma transacción.

La separación CQRS es lógica: lecturas y escrituras tienen mensajes y handlers
distintos, pero comparten PostgreSQL. No se usa event sourcing ni una segunda
base de lectura en esta etapa.

## Módulos

Cada carpeta dentro de `app/modules` se divide en `api`, `application`,
`domain` e `infrastructure`:

- `auth`: usuarios, contraseñas, JWT y refresh tokens rotativos.
- `businesses`: negocios, slugs, miembros, roles y aislamiento multi-tenant.
- `sites`: tema, publicación y bloques tipados de landing.
- `forms`: definición de campos y recepción validada de solicitudes.
- `catalog`: categorías, productos/servicios, imágenes, relaciones y ofertas.
- `orders`: pedidos invitados, snapshots de precios, estados e idempotencia.
- `notifications`: outbox y entregas por email con reintentos.
- `analytics`: visitas, vistas de productos, pedidos y métricas agregadas.

## Base de datos

Los identificadores son UUID, las fechas incluyen zona horaria y el dinero usa
`NUMERIC(14, 2)` más código de moneda. Las entidades editables se archivan; el
historial transaccional no se elimina.

### Identidad y tenencia

- `users` y `refresh_tokens` representan identidad y sesiones revocables.
- `businesses` contiene identidad pública, contacto, moneda y publicación.
- `business_members` relaciona muchos usuarios con muchos negocios usando los
  roles `owner`, `admin`, `editor` y `viewer`.
- Toda operación administrativa comprueba membresía en el handler o servicio,
  nunca acepta `business_id` como autorización suficiente.

### Sitio y formularios

- `site_templates`, `business_sites` y `site_sections` representan plantillas,
  tema y bloques `hero`, `text`, `gallery`, `contact` o `form`.
- El contenido variable usa JSONB validado por el command correspondiente.
- `forms`, `form_fields` y `form_submissions` almacenan esquemas y respuestas.
- Los archivos se representan como URLs externas.

### Catálogo y pedidos

- `categories`, `products`, `product_images`, `product_relations` y
  `product_offers` forman el catálogo aislado por negocio.
- `orders` exige clave de idempotencia única por negocio.
- `order_items` conserva nombre y precio aunque el producto cambie.
- `order_status_history` audita las transiciones entre `pending`, `confirmed`,
  `in_progress`, `completed` y `cancelled`.

### Operación

- `outbox_events` conserva trabajo asíncrono dentro de la transacción original.
- `notification_deliveries` registra proveedor, intentos, resultado y errores.
- `analytics_events` registra eventos mínimos con referencia anónima.

## API inicial

### Matriz de autorización

Todas las rutas bajo `/api/v1/businesses` requieren JWT Bearer. Los permisos se
resuelven en `BusinessAuthorizationService`, no en las rutas:

| Rol | Leer | Estadísticas | Contenido | Pedidos | Miembros | Negocio |
|---|---:|---:|---:|---:|---:|---:|
| `owner` | Sí | Sí | Sí | Sí | Sí | Sí |
| `admin` | Sí | Sí | Sí | Sí | Sí | Sí |
| `editor` | Sí | No | Sí | No | No | No |
| `viewer` | Sí | Sí | No | No | No | No |
| Administrador global | Sí | Sí | Sí | Sí | Sí | Sí |

El archivado de un negocio queda reservado al `owner` o al administrador
global. Las rutas públicas solo exponen contenido publicado, recepción de
formularios, creación idempotente de pedidos y tracking limitado.

### Contratos

Todos los endpoints usan el prefijo `/api/v1`.

- Autenticación: registro, login, refresh y usuario actual.
- Administración: negocios, landing, formularios, categorías y productos.
- Público: landing y catálogo por slug, solicitudes de formularios y pedidos.
- Los pedidos públicos requieren `Idempotency-Key` y al menos un medio de
  contacto.
- Los listados futuros deben responder con `items`, `total`, `page` y
  `page_size`.

## Evolución recomendada

1. Completar invitaciones, cambio de roles, verificación y recuperación.
2. Añadir edición/archivo de bloques, categorías, productos y formularios.
3. Incorporar transición administrativa de pedidos con matriz de estados.
4. Ejecutar un worker de outbox con proveedor SMTP y reintentos exponenciales.
5. Añadir commands de tracking y queries de dashboards por negocio/plataforma.
6. Evaluar proyecciones de lectura solo cuando las métricas reales lo exijan.

## Criterios de calidad

- Ninguna ruta puede importar modelos SQLAlchemy o repositorios concretos.
- Commands deben confirmar o revertir una única transacción.
- Queries no pueden hacer escrituras.
- Las pruebas deben cubrir handlers con repositorios falsos, contratos de
  repositorios, PostgreSQL real, aislamiento de tenants, idempotencia y outbox.
- Una migración Alembic debe acompañar cada cambio de esquema.
- `pytest`, `ruff check`, `ruff format --check` y `docker compose config` deben
  pasar antes de integrar cambios.
