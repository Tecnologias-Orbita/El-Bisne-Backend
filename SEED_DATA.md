# Datos de prueba de El Bisne

Este documento describe los datos creados por `python -m app.cli.seed`. El comando es idempotente: puede ejecutarse nuevamente para restaurar contraseñas, propietarios, contenido y estados de demostración.

## Ejecutar el seed

Con el entorno virtual local:

```bash
.venv/bin/python -m app.cli.seed
```

Con Docker:

```bash
docker compose exec api python -m app.cli.seed
```

## Acceso a la plataforma

| Rol | Email | Contraseña | Destino después del login |
|---|---|---|---|
| Administrador global | `admin@elbisne.dev` | `Admin123!` | Panel global `/admin` |
| Owner de Café Bisne Demo | `owner.demo@elbisne.dev` | `Demo123!` | Administración de Café Bisne Demo |
| Owner de Dulce Alma | `dulce.alma@elbisne.dev` | `Dulce123!` | Administración de Dulce Alma |
| Owner de Estudio Horizonte | `horizonte@elbisne.dev` | `Horizonte123!` | Administración de Estudio Horizonte |
| Owner de Próximo Bisne | `proximo@elbisne.dev` | `Proximo123!` | Administración de Próximo Bisne |

Estas credenciales son exclusivamente para desarrollo y no deben utilizarse en producción.

## Negocios

| Negocio | URL pública | Owner | Venta online | Visibilidad inicial | Contenido |
|---|---|---|---|---|---|
| Café Bisne Demo | `/bisne/cafe-bisne-demo` | `owner.demo@elbisne.dev` | No | Publicado | 6 productos y 2 servicios |
| Dulce Alma | `/bisne/dulce-alma` | `dulce.alma@elbisne.dev` | Sí | Publicado | 6 productos |
| Estudio Horizonte | `/bisne/estudio-horizonte` | `horizonte@elbisne.dev` | Sí | Publicado | 2 productos y 1 servicio |
| Próximo Bisne | `/bisne/proximo-bisne` | `proximo@elbisne.dev` | No | En mantenimiento | Sin productos ni servicios |

## Casos que permite probar

- **Café Bisne Demo:** catálogo de productos y servicios sin pedidos online.
- **Dulce Alma:** productos, carrito, checkout, persistencia del pedido y WhatsApp.
- **Estudio Horizonte:** productos y servicios coexistiendo con venta online.
- **Próximo Bisne:** negocio recién creado, accesible para su owner y con página pública de mantenimiento hasta activar `Publicar mi bisne`.
- **Administrador global:** búsqueda y administración de todos los negocios, pagos, categorías y rechazo/archivado.

## Visibilidad y rechazo

- Un negocio nuevo se crea con `is_published=false`.
- El owner puede administrarlo inmediatamente y activar **Publicar mi bisne** cuando esté listo.
- Mientras no esté publicado, su URL muestra una pantalla de mantenimiento y no aparece en descubrimiento.
- Rechazar o archivar desde el panel global establece `archived_at`, bloquea el acceso público y administrativo y elimina las imágenes gestionadas en Supabase Storage.
