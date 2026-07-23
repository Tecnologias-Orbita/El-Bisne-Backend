# Informe de pruebas end-to-end

Fecha de ejecución: 21 de julio de 2026.

## Entorno

- Aplicación FastAPI cargada mediante `TestClient`.
- PostgreSQL 17 real ejecutándose en Docker.
- Base aislada: `el_bisne_test`.
- Usuario aislado: `el_bisne_test`.
- La base de desarrollo `el_bisne` no fue limpiada ni modificada.
- No se construyeron imágenes ni se descargaron dependencias.

## Cobertura ejecutada

### Sistema y autenticación

- `GET /`.
- `GET /api/v1/health`.
- Registro, login y consulta de usuario actual.
- Rotación de refresh token.
- Rechazo de refresh token reutilizado.
- Rechazo de Bearer ausente o inválido.

### Negocios y permisos

- Crear, listar, consultar, actualizar y archivar negocios.
- Agregar, listar, cambiar rol y eliminar miembros.
- Acceso de propietario.
- Restricciones de `editor`.
- Rechazo de usuarios sin membresía.
- Acceso global de administrador de plataforma.

### Sitio

- Consultar y actualizar configuración.
- Crear, actualizar y eliminar secciones.
- Comprobar que el sitio no publicado devuelve `404`.
- Publicar y consultar la landing pública.

### Catálogo

- Crear, listar y actualizar categorías.
- Crear, listar, consultar, actualizar y archivar productos.
- Consultar catálogo público.
- Rechazar eliminación de categorías que contienen productos.
- Validar precio monetario serializado.

### Formularios

- Crear, listar, consultar y actualizar formularios.
- Enviar una respuesta pública validada.
- Listar respuestas administrativas.
- Cambiar estado de una respuesta.
- Archivar formularios que ya tienen respuestas.

### Pedidos y analítica

- Registrar una visita pública.
- Crear un pedido invitado con `Idempotency-Key`.
- Repetir el pedido sin duplicarlo.
- Listar y consultar el pedido desde administración.
- Ejecutar una transición válida de estado.
- Rechazar una transición inválida.
- Consultar visitas, pedidos y conversión del negocio.

## Resultado

```text
9 escenarios E2E aprobados
10 pruebas unitarias/arquitectónicas aprobadas
Ruff aprobado
Formato aprobado
git diff --check aprobado
```

La ejecución mostró una advertencia de deprecación de `TestClient` proveniente
de FastAPI/Starlette. No afecta los resultados, pero conviene migrar la suite a
la alternativa recomendada por esas dependencias cuando se actualicen.

## Ejecución local

Con PostgreSQL y la base aislada disponibles:

```bash
uv run pytest tests/e2e -vv
```

Las fixtures recrean exclusivamente las tablas de `el_bisne_test` antes de cada
caso. Nunca se debe configurar esta suite para usar una base con datos reales.
