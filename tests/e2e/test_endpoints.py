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
            "sells_online": True,
            "transaction_number": f"txn-{slug}",
            "plan": "basic",
            "phone_number": "+5355555555",
            "execution_date": "2026-07-01",
            "expiration_date": "2026-08-01",
            "amount_paid": "1000.00",
            "description": "Café de prueba",
            "currency": "USD",
            "timezone": "America/Havana",
            "contact_email": "owner@example.com",
            "contact_phone": "+5355555555",
            "hero_image_url": "https://example.com/hero.jpg",
            "logo_url": "https://example.com/logo.png",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def publish_business(client: TestClient, headers: dict[str, str], business: dict) -> dict:
    response = client.put(
        f"/api/v1/businesses/{business['id']}",
        headers=headers,
        json={
            "name": business["name"],
            "description": business["description"],
            "sells_online": business["sells_online"],
            "currency": business["currency"],
            "timezone": business["timezone"],
            "contact_email": business["contact_email"],
            "contact_phone": business["contact_phone"],
            "is_published": True,
            "hero_image_url": business["site"]["hero_image_url"],
            "logo_url": business["site"]["logo_url"],
        },
    )
    assert response.status_code == 200, response.text
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


def test_platform_billing_and_public_business_onboarding(client: TestClient) -> None:
    _, regular_headers = register_and_login(client, "regular@example.com")
    _, admin_headers = register_and_login(client, "platform@example.com")
    run_async(make_platform_admin("platform@example.com"))

    settings_url = "/api/v1/platform/payment-settings"
    admin_settings_url = "/api/v1/platform/admin/payment-settings"
    settings_body = {
        "bank_card": "9200123412341234",
        "confirmation_phone_number": "+5350000000",
    }
    assert client.get(settings_url).status_code == 404
    denied_settings = client.put(admin_settings_url, headers=regular_headers, json=settings_body)
    assert denied_settings.status_code == 403
    configured = client.put(admin_settings_url, headers=admin_headers, json=settings_body)
    assert configured.status_code == 200
    assert client.get(settings_url).json() == settings_body

    rates_admin_url = "/api/v1/platform/admin/exchange-rates"
    created_rate = client.post(
        rates_admin_url,
        headers=admin_headers,
        json={"currency": "usd", "value_in_cup": "350.250000"},
    )
    assert created_rate.status_code == 201, created_rate.text
    rate_id = created_rate.json()["id"]
    assert client.get("/api/v1/platform/exchange-rates").status_code in {401, 403}
    rates = client.get("/api/v1/platform/exchange-rates", headers=regular_headers)
    assert rates.json()[0]["currency"] == "USD"
    assert (
        client.put(
            f"{rates_admin_url}/{rate_id}",
            headers=admin_headers,
            json={"currency": "EUR", "value_in_cup": "390.000000"},
        ).status_code
        == 200
    )

    onboarding = client.post(
        "/api/v1/auth/register-business",
        json={
            "email": "new-owner@example.com",
            "password": "strong-password",
            "full_name": "Nueva Dueña",
            "business_name": "Nuevo negocio",
            "slug": "nuevo-negocio",
            "sells_online": False,
            "currency": "CUP",
            "transaction_number": "transfer-0001",
            "plan": "premium",
            "phone_number": "+5351111111",
            "execution_date": "2026-07-15",
            "expiration_date": "2026-08-15",
            "amount_paid": "2500.00",
        },
    )
    assert onboarding.status_code == 201, onboarding.text
    result = onboarding.json()
    assert result["user"]["email"] == "new-owner@example.com"
    assert result["business"]["slug"] == "nuevo-negocio"
    owner_headers = {"Authorization": f"Bearer {result['tokens']['access_token']}"}
    business_id = result["business"]["id"]

    owner_payments = client.get(
        f"/api/v1/businesses/{business_id}/subscription-payments",
        headers=owner_headers,
    )
    assert owner_payments.status_code == 200
    assert owner_payments.json()[0]["transaction_number"] == "transfer-0001"
    assert owner_payments.json()[0]["plan"] == "premium"
    assert owner_payments.json()[0]["execution_date"] == "2026-07-15"
    assert owner_payments.json()[0]["expiration_date"] == "2026-08-15"
    assert owner_payments.json()[0]["amount_paid"] == "2500.00"

    all_payments = client.get("/api/v1/platform/admin/subscription-payments", headers=admin_headers)
    assert all_payments.status_code == 200
    payment_id = all_payments.json()[0]["id"]
    payment_filters = {
        "payment_id": payment_id,
        "business_id": business_id,
        "business_name": "nuevo NEG",
        "transaction_number": "FER-000",
        "plan": "premium",
        "phone_number": "5111",
        "execution_date": "2026-07-15",
        "expiration_date": "2026-08-15",
        "amount_paid": "2500.00",
    }
    for filter_name, filter_value in payment_filters.items():
        filtered = client.get(
            "/api/v1/platform/admin/subscription-payments",
            headers=admin_headers,
            params={filter_name: filter_value},
        )
        assert filtered.status_code == 200, filtered.text
        assert [payment["id"] for payment in filtered.json()] == [payment_id]

    no_name_match = client.get(
        "/api/v1/platform/admin/subscription-payments",
        headers=admin_headers,
        params={"business_name": "inexistente"},
    )
    assert no_name_match.status_code == 200
    assert no_name_match.json() == []

    updated_payment = client.put(
        f"/api/v1/platform/admin/subscription-payments/{payment_id}",
        headers=admin_headers,
        json={
            "transaction_number": "transfer-0001-confirmed",
            "plan": "premium",
            "phone_number": "+5351111111",
            "execution_date": "2026-07-16",
            "expiration_date": "2026-09-16",
            "amount_paid": "3000.00",
        },
    )
    assert updated_payment.status_code == 200
    assert updated_payment.json()["transaction_number"] == "transfer-0001-confirmed"
    assert updated_payment.json()["amount_paid"] == "3000.00"
    assert client.delete(f"{rates_admin_url}/{rate_id}", headers=admin_headers).status_code == 204


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
            "sells_online": False,
            "currency": "CUP",
            "timezone": "America/Havana",
            "contact_email": "owner@example.com",
            "contact_phone": "+5355555555",
            "is_published": False,
            "hero_image_url": "https://example.com/new-hero.jpg",
            "logo_url": "https://example.com/new-logo.png",
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


def test_business_always_includes_fixed_template_information(client: TestClient) -> None:
    _, headers = register_and_login(client, "site@example.com")
    business = create_business(client, headers, "sitio-demo")
    business_url = f"/api/v1/businesses/{business['id']}"

    managed = client.get(business_url, headers=headers)
    assert managed.status_code == 200
    assert managed.json()["site"] == {
        "hero_image_url": "https://example.com/hero.jpg",
        "logo_url": "https://example.com/logo.png",
    }

    assert client.get("/api/v1/public/businesses/sitio-demo").status_code == 404
    published = publish_business(client, headers, business)
    public = client.get("/api/v1/public/businesses/sitio-demo")
    assert public.status_code == 200
    assert public.json() == published
    assert public.json()["name"] == "Café Sol"
    assert public.json()["description"] == "Café de prueba"
    assert public.json()["contact_email"] == "owner@example.com"
    assert client.get(f"{business_url}/site", headers=headers).status_code == 404


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

    publish_business(client, headers, business)
    public = client.get("/api/v1/public/businesses/catalogo-demo/catalog")
    assert public.status_code == 200
    assert public.json()["items"][0]["price"] == "4.00"

    assert (
        client.delete(f"{catalog_url}/categories/{category_id}", headers=headers).status_code == 409
    )
    assert client.delete(f"{catalog_url}/products/{product_id}", headers=headers).status_code == 204


def test_platform_categories_can_classify_businesses_and_products(client: TestClient) -> None:
    _, owner_headers = register_and_login(client, "classified@example.com")
    _, admin_headers = register_and_login(client, "categories-admin@example.com")
    run_async(make_platform_admin("categories-admin@example.com"))
    admin_url = "/api/v1/platform/admin/categories"

    denied = client.post(
        admin_url,
        headers=owner_headers,
        json={"name": "Gastronomía", "slug": "gastronomia"},
    )
    assert denied.status_code == 403
    created = client.post(
        admin_url,
        headers=admin_headers,
        json={
            "name": "Gastronomía",
            "slug": "gastronomia",
            "description": "Comida y bebida",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    platform_category_id = created.json()["id"]
    assert (
        client.get("/api/v1/platform/categories", headers=owner_headers).json()[0]["id"]
        == platform_category_id
    )

    business = create_business(client, owner_headers, "clasificado")
    business_url = f"/api/v1/businesses/{business['id']}"
    classified_business = client.put(
        business_url,
        headers=owner_headers,
        json={
            "name": business["name"],
            "description": business["description"],
            "sells_online": business["sells_online"],
            "currency": business["currency"],
            "timezone": business["timezone"],
            "contact_email": business["contact_email"],
            "contact_phone": business["contact_phone"],
            "is_published": False,
            "hero_image_url": business["site"]["hero_image_url"],
            "logo_url": business["site"]["logo_url"],
            "platform_category_id": platform_category_id,
        },
    )
    assert classified_business.status_code == 200, classified_business.text
    assert classified_business.json()["platform_category_id"] == platform_category_id

    catalog_url = f"{business_url}/catalog"
    product = client.post(
        f"{catalog_url}/products",
        headers=owner_headers,
        json={
            "name": "Producto clasificado",
            "slug": "producto-clasificado",
            "price": "10.00",
            "currency": "CUP",
            "platform_category_id": platform_category_id,
        },
    )
    assert product.status_code == 201, product.text
    assert product.json()["platform_category_id"] == platform_category_id

    assert (
        client.delete(f"{admin_url}/{platform_category_id}", headers=admin_headers).status_code
        == 204
    )
    assert client.get(business_url, headers=owner_headers).json()["platform_category_id"] is None
    assert (
        client.get(f"{catalog_url}/products/{product.json()['id']}", headers=owner_headers).json()[
            "platform_category_id"
        ]
        is None
    )


def test_services_are_public_but_cannot_be_ordered(client: TestClient) -> None:
    _, headers = register_and_login(client, "services@example.com")
    business = create_business(client, headers, "servicios-demo")
    service_url = f"/api/v1/businesses/{business['id']}/services"
    created = client.post(
        service_url,
        headers=headers,
        json={
            "name": "Sesión fotográfica",
            "slug": "sesion-fotografica",
            "description": "Retratos profesionales",
            "price": "1200.00",
            "currency": "CUP",
            "duration_minutes": 60,
            "is_published": True,
        },
    )
    assert created.status_code == 201, created.text
    service = created.json()
    assert service["duration_minutes"] == 60
    publish_business(client, headers, business)
    public = client.get("/api/v1/public/businesses/servicios-demo/services")
    assert public.status_code == 200
    assert [item["id"] for item in public.json()] == [service["id"]]
    rejected = client.post(
        "/api/v1/public/businesses/servicios-demo/orders",
        headers={"Idempotency-Key": "service-order"},
        json={
            "customer_name": "Cliente",
            "customer_phone": "+5355555555",
            "items": [{"product_id": service["id"], "quantity": 1}],
        },
    )
    assert rejected.status_code == 422


def test_business_without_online_sales_rejects_orders(client: TestClient) -> None:
    _, headers = register_and_login(client, "offline@example.com")
    business = create_business(client, headers, "offline-demo")
    business["sells_online"] = False
    publish_business(client, headers, business)
    response = client.post(
        "/api/v1/public/businesses/offline-demo/orders",
        headers={"Idempotency-Key": "offline-order"},
        json={
            "customer_name": "Cliente",
            "customer_phone": "+5355555555",
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
        },
    )
    assert response.status_code == 422
    assert "does not accept online orders" in response.json()["detail"]


def test_order_idempotency_status_and_analytics(client: TestClient) -> None:
    _, headers = register_and_login(client, "orders@example.com")
    business = create_business(client, headers, "pedidos-demo")
    business_id = business["id"]
    catalog_url = f"/api/v1/businesses/{business_id}/catalog"
    product = client.post(
        f"{catalog_url}/products",
        headers=headers,
        json={
            "name": "Producto",
            "slug": "producto",
            "price": "10.00",
            "currency": "USD",
            "is_published": True,
        },
    ).json()
    publish_business(client, headers, business)

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
