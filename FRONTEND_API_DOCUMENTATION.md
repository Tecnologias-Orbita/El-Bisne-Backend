# Contrato API para el frontend

Última revisión: 25 de julio de 2026.

Esta es la referencia funcional para construir el panel administrativo y la
vista pública. Describe el contrato implementado, no funcionalidades futuras.

## Convenciones

- Base local: `http://localhost:8000`.
- Prefijo: `/api/v1`.
- JSON: `Content-Type: application/json`.
- Rutas administrativas: `Authorization: Bearer <access_token>`.
- UUID e importes se reciben como strings. Ejemplo monetario: `"10.50"`.
- `204` nunca devuelve body.
- Swagger: `/docs`. Contrato procesable: `/openapi.json`.

Errores de aplicación:

```json
{"error":{"code":"forbidden","message":"You do not have permission"}}
```

La validación `422` usa el array `detail` estándar de FastAPI. El frontend debe
tratar `401` renovando la sesión una sola vez, `403` como falta de permiso,
`404` como inexistente/archivado/no publicado y `409` como conflicto.

## Cómo se crea la información de la presentación

No hay un endpoint separado para crearla. `POST /businesses` crea
atómicamente:

1. El negocio.
2. La membresía `owner` del creador.
3. Su extensión visual 1:1.

Se pueden enviar `hero_image_url` y `logo_url` al crear. Si no se envían, el
registro visual se crea con valores `null`. Después se actualiza todo mediante
`PUT /businesses/{business_id}`.

No existen endpoints `/site`, `/sections`, `/theme` ni `/palette`. La estructura
y los colores son fijos en el frontend para todos los negocios.

`BusinessDTO`, usado tanto en administración como en público:

```json
{
  "id": "uuid",
  "name": "Café Sol",
  "slug": "cafe-sol",
  "description": "Café y repostería artesanal",
  "business_type": "restaurant",
  "currency": "USD",
  "timezone": "America/Havana",
  "contact_email": "contacto@cafesol.com",
  "contact_phone": "+5355555555",
  "is_published": true,
  "site": {
    "hero_image_url": "https://cdn.example.com/hero.jpg",
    "logo_url": "https://cdn.example.com/logo.png"
  }
}
```

`site` es un nombre heredado del contrato y solo contiene esas dos imágenes.
Sus dos claves siempre existen, aunque tengan valor `null`.

## Roles

| Rol | Ver | Contenido | Pedidos | Analítica | Miembros | Negocio |
|---|---:|---:|---:|---:|---:|---:|
| `owner` | Sí | Sí | Sí | Sí | Sí | Sí |
| `admin` | Sí | Sí | Sí | Sí | Sí | Sí |
| `editor` | Sí | Sí | No | No | No | No |
| `viewer` | Sí | No | No | Sí | No | No |
| `platform_admin` | Sí | Sí | Sí | Sí | Sí | Sí |

## Sistema y autenticación

### `GET /`

Público. `200`: objeto con `message`.

### `GET /api/v1/health`

Público. `200`:

```json
{"status":"ok"}
```

### `POST /api/v1/auth/register`

Público.

```json
{
  "email": "user@example.com",
  "password": "minimum-8-characters",
  "full_name": "Nombre Apellidos"
}
```

`password`: 8–128 caracteres. `full_name`: 2–160. `201`:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Nombre Apellidos",
  "is_platform_admin": false
}
```

Email existente: `409`.

### `POST /api/v1/auth/login`

```json
{"email":"user@example.com","password":"minimum-8-characters"}
```

`200`:

```json
{
  "access_token": "jwt",
  "refresh_token": "opaque-token",
  "token_type": "bearer"
}
```

Credenciales inválidas: `401`.

### `POST /api/v1/auth/refresh`

```json
{"refresh_token":"opaque-token"}
```

`200`: nuevo `access_token`, `refresh_token` y `token_type`. El refresh enviado
queda revocado y el frontend debe reemplazarlo. Token inválido o reutilizado:
`401`.

### `GET /api/v1/auth/me`

Bearer. `200`: el DTO de usuario mostrado en registro.

## Negocios

### `POST /api/v1/businesses`

Bearer. Crea negocio, owner y extensión visual.

```json
{
  "name": "Café Sol",
  "slug": "cafe-sol",
  "business_type": "restaurant",
  "description": "Café y repostería",
  "currency": "USD",
  "timezone": "America/Havana",
  "contact_email": "contacto@cafesol.com",
  "contact_phone": "+5355555555",
  "hero_image_url": "https://cdn.example.com/hero.jpg",
  "logo_url": "https://cdn.example.com/logo.png"
}
```

Requeridos: `name` (2–160), `slug` (3–100), `business_type` (2–50).
Defaults: `currency=USD`, `timezone=America/Havana`, publicación `false`.
Contacto e imágenes aceptan `null`. `201`: `BusinessDTO`. Slug ocupado: `409`.

### `GET /api/v1/businesses`

Bearer. `200`: `BusinessDTO[]`. Un usuario normal recibe sus negocios; el
administrador global recibe todos los no archivados.

### `GET /api/v1/businesses/{business_id}`

Bearer y permiso de lectura. `200`: `BusinessDTO` completo. `403` sin permiso;
`404` inexistente o archivado.

### `PUT /api/v1/businesses/{business_id}`

Bearer y permiso para configurar negocio. Es un `PUT` completo:

```json
{
  "name": "Café Sol",
  "description": "Descripción actualizada",
  "business_type": "restaurant",
  "currency": "USD",
  "timezone": "America/Havana",
  "contact_email": "contacto@cafesol.com",
  "contact_phone": "+5355555555",
  "is_published": true,
  "hero_image_url": "https://cdn.example.com/hero-new.jpg",
  "logo_url": "https://cdn.example.com/logo-new.png"
}
```

Requeridos: `name`, `business_type`, `currency`, `timezone`. `200`:
`BusinessDTO`. El slug no se puede cambiar aquí.

Importante: omitir `is_published` lo cambia a `false`; omitir imágenes las
cambia a `null`. El frontend debe reenviar los valores actuales.

### `DELETE /api/v1/businesses/{business_id}`

Solo `owner` o administrador global. `204`. Archiva y despublica; no borra el
historial.

## Miembros

### `GET /api/v1/businesses/{business_id}/members`

Permiso de miembros. `200`:

```json
[
  {
    "id": "membership-uuid",
    "user_id": "user-uuid",
    "email": "editor@example.com",
    "full_name": "Editor",
    "role": "editor"
  }
]
```

### `POST /api/v1/businesses/{business_id}/members`

```json
{"email":"editor@example.com","role":"editor"}
```

Roles asignables: `admin`, `editor`, `viewer`. El usuario debe estar registrado
y no ser miembro. `204`.

### `PATCH /api/v1/businesses/{business_id}/members/{member_user_id}`

```json
{"role":"viewer"}
```

`204`. No permite modificar al owner.

### `DELETE /api/v1/businesses/{business_id}/members/{member_user_id}`

Permiso de miembros. `204`. No permite eliminar al owner.

## Categorías

### `POST /api/v1/businesses/{business_id}/catalog/categories`

Permiso de contenido.

```json
{"name":"Cafés","slug":"cafes"}
```

`name`: 1–120; `slug`: 3–100. `201`:

```json
{"id":"uuid","name":"Cafés","slug":"cafes"}
```

### `GET /api/v1/businesses/{business_id}/catalog/categories`

Permiso de lectura. `200`: array del DTO anterior.

### `PUT /api/v1/businesses/{business_id}/catalog/categories/{category_id}`

```json
{
  "name": "Cafés especiales",
  "slug": "cafes-especiales",
  "description": "Selección",
  "image_url": "https://cdn.example.com/category.jpg",
  "position": 0,
  "is_visible": true
}
```

Requeridos: `name`, `slug`. `position >= 0`. `200`: DTO resumido con `id`,
`name`, `slug`. La respuesta actual no devuelve descripción, imagen, posición
ni visibilidad.

### `DELETE /api/v1/businesses/{business_id}/catalog/categories/{category_id}`

Permiso de contenido. `204`; `409` si contiene productos.

## Productos

`ProductDTO`:

```json
{
  "id": "uuid",
  "category_id": "uuid-or-null",
  "name": "Café cubano",
  "slug": "cafe-cubano",
  "product_type": "product",
  "description": "Café fuerte",
  "price": "2.50",
  "currency": "USD",
  "image_url": "https://cdn.example.com/product.jpg",
  "is_available": true
}
```

### `POST /api/v1/businesses/{business_id}/catalog/products`

```json
{
  "name": "Café cubano",
  "slug": "cafe-cubano",
  "product_type": "product",
  "price": "2.50",
  "currency": "USD",
  "category_id": null,
  "description": "Café fuerte",
  "image_url": "https://cdn.example.com/product.jpg",
  "is_published": true
}
```

Permiso de contenido. Requeridos: `name`, `slug`, `price`. `product_type`:
`product` o `service`; precio no negativo con máximo dos decimales. Defaults:
`product_type=product`, `currency=USD`, publicación `false`. `201`:
`ProductDTO`.

### `GET /api/v1/businesses/{business_id}/catalog/products`

Permiso de lectura. `200`: `ProductDTO[]`.

### `GET /api/v1/businesses/{business_id}/catalog/products/{product_id}`

Permiso de lectura. `200`: `ProductDTO`.

### `PUT /api/v1/businesses/{business_id}/catalog/products/{product_id}`

```json
{
  "category_id": null,
  "name": "Café cubano doble",
  "slug": "cafe-cubano-doble",
  "product_type": "product",
  "description": "Dos shots",
  "price": "4.00",
  "currency": "USD",
  "image_url": "https://cdn.example.com/product.jpg",
  "is_available": true,
  "is_published": true,
  "track_inventory": false,
  "stock_quantity": null
}
```

Permiso de contenido. Requeridos: `name`, `slug`, `product_type`, `price`,
`currency`. `stock_quantity >= 0`. `200`: `ProductDTO`. El DTO actual no
devuelve publicación ni inventario.

### `DELETE /api/v1/businesses/{business_id}/catalog/products/{product_id}`

Permiso de contenido. `204`. Archiva y marca no publicado/no disponible.

## Pedidos administrativos

Estados: `pending`, `confirmed`, `in_progress`, `completed`, `cancelled`.

### `GET /api/v1/businesses/{business_id}/orders`

Permiso de pedidos. Filtro opcional `?order_status=pending`. `200`:

```json
[
  {
    "id": "uuid",
    "order_number": "ORD-000001",
    "status": "pending",
    "currency": "USD",
    "subtotal": "20.00",
    "total": "20.00"
  }
]
```

### `GET /api/v1/businesses/{business_id}/orders/{order_id}`

Permiso de pedidos. `200`:

```json
{
  "id": "uuid",
  "order_number": "ORD-000001",
  "status": "pending",
  "currency": "USD",
  "subtotal": "20.00",
  "total": "20.00",
  "customer_name": "Cliente",
  "customer_email": "client@example.com",
  "customer_phone": null,
  "notes": null,
  "items": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "product_name": "Servicio",
      "unit_price": "10.00",
      "quantity": 2,
      "line_total": "20.00"
    }
  ]
}
```

### `PATCH /api/v1/businesses/{business_id}/orders/{order_id}/status`

```json
{"status":"confirmed","comment":"Pedido aceptado"}
```

Permiso de pedidos. Comentario opcional, máximo 1000. `200`: resumen de pedido.
Transición inválida: `422`. Flujo normal:
`pending → confirmed → in_progress → completed`.

## Analítica

### `GET /api/v1/businesses/{business_id}/analytics`

Permiso de analítica. `200`:

```json
{
  "visits": 100,
  "product_views": 40,
  "orders": 5,
  "completed_orders": 3,
  "conversion_rate": 5.0
}
```

Conversión: `orders / visits * 100`; sin visitas devuelve `0`.

## API pública

### `GET /api/v1/public/businesses/{business_slug}`

`200`: `BusinessDTO` completo para renderizar hero, logo, descripción y
contacto. `404` si no está publicado o está archivado.

### `GET /api/v1/public/businesses/{business_slug}/catalog`

Solo negocio y productos públicos/disponibles. `200`:

```json
{
  "business_id": "uuid",
  "business_name": "Café Sol",
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 100
}
```

`items` contiene `ProductDTO`. Actualmente no recibe parámetros de paginación.

### `POST /api/v1/public/businesses/{business_slug}/orders`

Header obligatorio de 8–100 caracteres:

```http
Idempotency-Key: checkout-unique-0001
```

```json
{
  "customer_name": "Cliente",
  "customer_email": "client@example.com",
  "customer_phone": null,
  "notes": "Entregar por la tarde",
  "items": [{"product_id":"uuid","quantity":2}]
}
```

`customer_name`: 2–160. Debe haber al menos un contacto. `items`: 1–100;
cantidad: 1–999. `201`: resumen de pedido. Al reintentar el mismo checkout se
debe reutilizar la clave para recibir el mismo pedido sin duplicarlo.

### `POST /api/v1/public/businesses/{business_slug}/events`

```json
{
  "event_type": "product_view",
  "resource_id": "product-uuid",
  "anonymous_reference": "visitor-session-id"
}
```

Tipos admitidos: `site_view`, `product_view`. Para `product_view`,
`resource_id` identifica el producto. `anonymous_reference` es opcional,
máximo 64, y no debe contener información personal. `204`.

## Limitaciones relevantes para el frontend

No existen actualmente:

- Logout, verificación o recuperación de contraseña.
- Invitaciones por email; el miembro debe estar registrado.
- Restauración de recursos archivados.
- Endpoint público de producto individual por slug.
- Paginación real en listados administrativos.
- CRUD HTTP de ofertas, relaciones o imágenes adicionales.
- Administración global de usuarios o dashboard global.
- Carga de archivos; se envían URLs externas.

## Flujos recomendados

Panel:

```text
login → guardar tokens → GET /auth/me → GET /businesses
→ seleccionar business_id → GET /businesses/{business_id}
```

Alta y publicación:

```text
POST /businesses (crea también información visual)
→ recibe is_published=false
→ PUT /businesses/{id} con el recurso completo e is_published=true
→ GET público por slug comienza a responder 200
```

Vista pública:

```text
GET /public/businesses/{slug}
→ renderizar información y hero con plantilla fija
GET /public/businesses/{slug}/catalog
→ renderizar productos
```
