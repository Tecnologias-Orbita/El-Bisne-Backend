import uuid

import pytest

from app.modules.businesses.application.services.authorization import (
    ROLE_PERMISSIONS,
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.shared.domain.exceptions import ForbiddenError


class ScalarSession:
    def __init__(self, *values: object) -> None:
        self.values = iter(values)

    async def scalar(self, _: object) -> object:
        return next(self.values)


@pytest.mark.asyncio
async def test_platform_admin_can_access_any_business() -> None:
    user_id = uuid.uuid4()
    service = BusinessAuthorizationService(ScalarSession(user_id, True))  # type: ignore[arg-type]

    role = await service.require(user_id, uuid.uuid4(), BusinessPermission.MANAGE_ORDERS)

    assert role == "platform_admin"


@pytest.mark.asyncio
async def test_editor_cannot_manage_orders() -> None:
    user_id = uuid.uuid4()
    service = BusinessAuthorizationService(ScalarSession(user_id, False, "editor"))  # type: ignore[arg-type]

    with pytest.raises(ForbiddenError):
        await service.require(user_id, uuid.uuid4(), BusinessPermission.MANAGE_ORDERS)


def test_role_permission_matrix_is_restrictive() -> None:
    assert BusinessPermission.MANAGE_MEMBERS in ROLE_PERMISSIONS["owner"]
    assert BusinessPermission.MANAGE_ORDERS in ROLE_PERMISSIONS["admin"]
    assert BusinessPermission.MANAGE_CONTENT in ROLE_PERMISSIONS["editor"]
    assert BusinessPermission.MANAGE_ORDERS not in ROLE_PERMISSIONS["editor"]
    assert ROLE_PERMISSIONS["viewer"] == {
        BusinessPermission.VIEW,
        BusinessPermission.VIEW_ANALYTICS,
    }


def test_all_business_management_routes_require_bearer_authentication() -> None:
    from app.main import app

    paths = app.openapi()["paths"]
    for path, operations in paths.items():
        if not path.startswith("/api/v1/businesses"):
            continue
        for method, operation in operations.items():
            if method == "parameters":
                continue
            assert operation.get("security"), f"{method.upper()} {path} is public"
