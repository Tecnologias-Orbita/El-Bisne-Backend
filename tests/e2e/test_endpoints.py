import uuid

from fastapi.testclient import TestClient

from tests.e2e.conftest import make_platform_admin, register_and_login, run_async


def create_business(client: TestClient, headers: dict[str, str], slug: str = "cafe-sol") -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers=headers,
        json={
            "name": "Café Sol",
            "slug": slug,
            "business_type": "restaurant",
            "description": "Café de prueba",
            "currency": "USD",
            "timezone": "America/Havana",
            "contact_email": "owner@example.com",
            "contact_phone": "+5355555555",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_system_endpoints(client: TestClient) -> None:
    root = client.get("/")
    health = client.get("/api/v1/health")

    assert root.status_code == 200
    assert "message" in root.json()
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_authentication_endpoints_and_invalid_token(client: TestClient) -> None:
    tokens, headers = register_and_login(client, "auth@example.com")

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "auth@example.com"

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    assert client.get("/api/v1/auth/me").status_code in {401, 403}
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}).status_code
        == 401
    )


def test_business_member_crud_and_role_protection(client: TestClient) -> None:
    _, owner_headers = register_and_login(client, "owner@example.com")
    _, editor_headers = register_and_login(client, "editor@example.com")
    business = create_business(client, owner_headers)
    business_url = f"/api/v1/businesses/{business['id']}"

    assert client.get("/api/v1/businesses", headers=owner_headers).status_code == 200
    assert client.get(business_url, headers=owner_headers).status_code == 200

    updated = client.put(
        business_url,
        headers=owner_headers,
        json={
            "name": "Café Sol Actualizado",
            "description": "Nueva descripción",
            "business_type": "restaurant",
            "currency": "CUP",
            "timezone": "America/Havana",
            "contact_email": "owner@example.com",
            "contact_phone": "+5355555555",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["currency"] == "CUP"

    members_url = f"{business_url}/members"
    added = client.post(
        members_url,
        headers=owner_headers,
        json={"email": "editor@example.com", "role": "editor"},
    )
    assert added.status_code == 204
    members = client.get(members_url, headers=owner_headers)
    assert members.status_code == 200
    editor_id = next(x["user_id"] for x in members.json() if x["email"] == "editor@example.com")

    assert client.get(business_url, headers=editor_headers).status_code == 200
    assert client.get(members_url, headers=editor_headers).status_code == 403
    assert client.get(f"{business_url}/orders", headers=editor_headers).status_code == 403

    changed = client.patch(
        f"{members_url}/{editor_id}",
        headers=owner_headers,
        json={"role": "viewer"},
    )
    assert changed.status_code == 204
    removed = client.delete(f"{members_url}/{editor_id}", headers=owner_headers)
    assert removed.status_code == 204
    assert client.get(business_url, headers=editor_headers).status_code == 403

    assert client.delete(business_url, headers=owner_headers).status_code == 204
    assert client.get(business_url, headers=owner_headers).status_code == 404


def test_site_section_crud_and_public_visibility(client: TestClient) -> None:
    _, headers = register_and_login(client, "site@example.com")
    business = create_business(client, headers, "sitio-demo")
    site_url = f"/api/v1/businesses/{business['id']}/site"

    assert client.get(site_url, headers=headers).status_code == 200
    assert (
        client.put(
            site_url,
            headers=headers,
            json={
                "favicon_url": "https://example.com/icon.png",
                "palette": {"primary": "#112233"},
                "typography": {"heading": "Inter"},
                "seo": {"title": "Sitio demo"},
            },
        ).status_code
        == 204
    )

    section = client.post(
        f"{site_url}/sections",
        headers=headers,
        json={"section_type": "hero", "position": 0, "content": {"title": "Hola"}},
    )
    assert section.status_code == 201
    section_id = section.json()["id"]
    assert (
        client.put(
            f"{site_url}/sections/{section_id}",
            headers=headers,
            json={
                "section_type": "hero",
                "position": 0,
                "content": {"title": "Bienvenido"},
                "is_visible": True,
            },
        ).status_code
        == 200
    )

    assert client.get("/api/v1/public/businesses/sitio-demo").status_code == 404
    assert client.post(f"{site_url}/publish", headers=headers).status_code == 204
    public = client.get("/api/v1/public/businesses/sitio-demo")
    assert public.status_code == 200
    assert public.json()["sections"][0]["content"]["title"] == "Bienvenido"

    assert client.delete(f"{site_url}/sections/{section_id}", headers=headers).status_code == 204


def test_catalog_crud_and_public_catalog(client: TestClient) -> None:
    _, headers = register_and_login(client, "catalog@example.com")
    business = create_business(client, headers, "catalogo-demo")
    catalog_url = f"/api/v1/businesses/{business['id']}/catalog"

    category = client.post(
        f"{catalog_url}/categories",
        headers=headers,
        json={"name": "Cafés", "slug": "cafes"},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]
    assert client.get(f"{catalog_url}/categories", headers=headers).status_code == 200
    assert (
        client.put(
            f"{catalog_url}/categories/{category_id}",
            headers=headers,
            json={
                "name": "Cafés especiales",
                "slug": "cafes-especiales",
                "description": "Selección",
                "position": 1,
                "is_visible": True,
            },
        ).status_code
        == 200
    )

    product = client.post(
        f"{catalog_url}/products",
        headers=headers,
        json={
            "name": "Café cubano",
            "slug": "cafe-cubano",
            "product_type": "product",
            "price": "2.50",
            "currency": "USD",
            "category_id": category_id,
            "is_published": True,
        },
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert client.get(f"{catalog_url}/products", headers=headers).status_code == 200
    assert client.get(f"{catalog_url}/products/{product_id}", headers=headers).status_code == 200
    assert (
        client.put(
            f"{catalog_url}/products/{product_id}",
            headers=headers,
            json={
                "name": "Café cubano doble",
                "slug": "cafe-cubano-doble",
                "product_type": "product",
                "price": "4.00",
                "currency": "USD",
                "category_id": category_id,
                "is_available": True,
                "is_published": True,
                "track_inventory": False,
            },
        ).status_code
        == 200
    )

    assert (
        client.post(
            f"/api/v1/businesses/{business['id']}/site/publish", headers=headers
        ).status_code
        == 204
    )
    public = client.get("/api/v1/public/businesses/catalogo-demo/catalog")
    assert public.status_code == 200
    assert public.json()["items"][0]["price"] == "4.00"

    assert (
        client.delete(f"{catalog_url}/categories/{category_id}", headers=headers).status_code == 409
    )
    assert client.delete(f"{catalog_url}/products/{product_id}", headers=headers).status_code == 204


def test_form_crud_public_submission_and_management(client: TestClient) -> None:
    _, headers = register_and_login(client, "forms@example.com")
    business = create_business(client, headers, "formularios-demo")
    forms_url = f"/api/v1/businesses/{business['id']}/forms"
    client.post(f"/api/v1/businesses/{business['id']}/site/publish", headers=headers)

    form = client.post(
        forms_url,
        headers=headers,
        json={
            "name": "Contacto",
            "description": "Solicitud",
            "fields": [
                {
                    "name": "message",
                    "label": "Mensaje",
                    "field_type": "textarea",
                    "position": 0,
                    "is_required": True,
                    "config": {},
                }
            ],
        },
    )
    assert form.status_code == 201
    form_id = form.json()["id"]
    assert client.get(forms_url, headers=headers).status_code == 200
    assert client.get(f"{forms_url}/{form_id}", headers=headers).status_code == 200
    assert (
        client.put(
            f"{forms_url}/{form_id}",
            headers=headers,
            json={
                "name": "Contacto actualizado",
                "description": "Solicitud",
                "status": "published",
                "fields": [
                    {
                        "name": "message",
                        "label": "Mensaje",
                        "field_type": "textarea",
                        "position": 0,
                        "is_required": True,
                        "config": {},
                    }
                ],
            },
        ).status_code
        == 200
    )

    submission = client.post(
        f"/api/v1/public/businesses/formularios-demo/forms/{form_id}/submissions",
        json={"data": {"message": "Necesito información"}, "contact_email": "client@example.com"},
    )
    assert submission.status_code == 201, submission.text
    submission_id = submission.json()["id"]
    managed = client.get(f"{forms_url}/management/submissions", headers=headers)
    assert managed.status_code == 200
    assert len(managed.json()) == 1
    assert (
        client.patch(
            f"{forms_url}/management/submissions/{submission_id}",
            headers=headers,
            json={"status": "closed"},
        ).status_code
        == 200
    )
    assert client.delete(f"{forms_url}/{form_id}", headers=headers).status_code == 204
    assert client.get(f"{forms_url}/{form_id}", headers=headers).json()["status"] == "archived"


def test_order_idempotency_status_and_analytics(client: TestClient) -> None:
    _, headers = register_and_login(client, "orders@example.com")
    business = create_business(client, headers, "pedidos-demo")
    business_id = business["id"]
    catalog_url = f"/api/v1/businesses/{business_id}/catalog"
    product = client.post(
        f"{catalog_url}/products",
        headers=headers,
        json={
            "name": "Servicio",
            "slug": "servicio",
            "product_type": "service",
            "price": "10.00",
            "currency": "USD",
            "is_published": True,
        },
    ).json()
    client.post(f"/api/v1/businesses/{business_id}/site/publish", headers=headers)

    assert (
        client.post(
            "/api/v1/public/businesses/pedidos-demo/events",
            json={"event_type": "site_view", "anonymous_reference": "visitor-1"},
        ).status_code
        == 204
    )
    order_body = {
        "customer_name": "Cliente",
        "customer_email": "client@example.com",
        "items": [{"product_id": product["id"], "quantity": 2}],
    }
    idempotency_headers = {"Idempotency-Key": "order-e2e-0001"}
    first = client.post(
        "/api/v1/public/businesses/pedidos-demo/orders",
        headers=idempotency_headers,
        json=order_body,
    )
    assert first.status_code == 201, first.text
    repeated = client.post(
        "/api/v1/public/businesses/pedidos-demo/orders",
        headers=idempotency_headers,
        json=order_body,
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]

    orders_url = f"/api/v1/businesses/{business_id}/orders"
    assert len(client.get(orders_url, headers=headers).json()) == 1
    order_id = first.json()["id"]
    assert client.get(f"{orders_url}/{order_id}", headers=headers).status_code == 200
    assert (
        client.patch(
            f"{orders_url}/{order_id}/status",
            headers=headers,
            json={"status": "confirmed", "comment": "Aceptado"},
        ).status_code
        == 200
    )
    invalid_transition = client.patch(
        f"{orders_url}/{order_id}/status",
        headers=headers,
        json={"status": "completed"},
    )
    assert invalid_transition.status_code == 422

    dashboard = client.get(f"/api/v1/businesses/{business_id}/analytics", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["visits"] == 1
    assert dashboard.json()["orders"] == 1


def test_platform_admin_can_manage_unrelated_business(client: TestClient) -> None:
    _, owner_headers = register_and_login(client, "tenant-owner@example.com")
    _, outsider_headers = register_and_login(client, "outsider@example.com")
    business = create_business(client, owner_headers, "tenant-protegido")
    business_url = f"/api/v1/businesses/{business['id']}"

    assert client.get(business_url, headers=outsider_headers).status_code == 403
    run_async(make_platform_admin("outsider@example.com"))
    assert client.get(business_url, headers=outsider_headers).status_code == 200
    assert client.get(f"{business_url}/analytics", headers=outsider_headers).status_code == 200
    assert any(
        item["id"] == business["id"]
        for item in client.get("/api/v1/businesses", headers=outsider_headers).json()
    )


def test_unknown_business_is_never_accessible_to_regular_client(client: TestClient) -> None:
    _, headers = register_and_login(client, "client-only@example.com")
    unknown_id = uuid.uuid4()

    assert client.get(f"/api/v1/businesses/{unknown_id}", headers=headers).status_code == 403
    assert (
        client.get(f"/api/v1/businesses/{unknown_id}/catalog/products", headers=headers).status_code
        == 403
    )
    assert client.get(f"/api/v1/businesses/{unknown_id}/orders", headers=headers).status_code == 403
