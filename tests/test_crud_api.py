from app.main import app


def test_management_aggregates_expose_crud_contracts() -> None:
    paths = app.openapi()["paths"]

    expected_methods = {
        "/api/v1/businesses": {"get", "post"},
        "/api/v1/businesses/{business_id}": {"get", "put", "delete"},
        "/api/v1/businesses/{business_id}/members": {"get", "post"},
        "/api/v1/businesses/{business_id}/catalog/categories": {"get", "post"},
        "/api/v1/businesses/{business_id}/catalog/categories/{category_id}": {
            "put",
            "delete",
        },
        "/api/v1/businesses/{business_id}/catalog/products": {"get", "post"},
        "/api/v1/businesses/{business_id}/catalog/products/{product_id}": {
            "get",
            "put",
            "delete",
        },
        "/api/v1/businesses/{business_id}/orders": {"get"},
        "/api/v1/businesses/{business_id}/orders/{order_id}": {"get"},
        "/api/v1/businesses/{business_id}/orders/{order_id}/status": {"patch"},
        "/api/v1/platform/payment-settings": {"get"},
        "/api/v1/platform/exchange-rates": {"get"},
        "/api/v1/platform/admin/payment-settings": {"put"},
        "/api/v1/platform/admin/exchange-rates": {"post"},
        "/api/v1/platform/admin/exchange-rates/{rate_id}": {"put", "delete"},
        "/api/v1/platform/admin/subscription-payments": {"get", "post"},
        "/api/v1/platform/admin/subscription-payments/{payment_id}": {
            "put",
            "delete",
        },
        "/api/v1/businesses/{business_id}/subscription-payments": {"get"},
        "/api/v1/auth/register-business": {"post"},
    }

    for path, methods in expected_methods.items():
        assert path in paths
        assert methods <= set(paths[path])
