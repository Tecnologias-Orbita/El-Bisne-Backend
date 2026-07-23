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
        "/api/v1/businesses/{business_id}/forms": {"get", "post"},
        "/api/v1/businesses/{business_id}/forms/{form_id}": {"get", "put", "delete"},
        "/api/v1/businesses/{business_id}/site": {"get", "put"},
        "/api/v1/businesses/{business_id}/site/sections": {"post"},
        "/api/v1/businesses/{business_id}/site/sections/{section_id}": {
            "put",
            "delete",
        },
        "/api/v1/businesses/{business_id}/orders": {"get"},
        "/api/v1/businesses/{business_id}/orders/{order_id}": {"get"},
        "/api/v1/businesses/{business_id}/orders/{order_id}/status": {"patch"},
    }

    for path, methods in expected_methods.items():
        assert path in paths
        assert methods <= set(paths[path])
