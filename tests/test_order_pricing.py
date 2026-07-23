import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.orders.application.dto.orders import OrderItemInput
from app.modules.orders.application.services.order_pricing import calculate_order
from app.shared.domain.exceptions import ValidationError


def test_calculate_order_uses_decimal_prices() -> None:
    product_id = uuid.uuid4()
    product = SimpleNamespace(id=product_id, price=Decimal("10.25"))

    lines, total = calculate_order([OrderItemInput(product_id, 2)], [product])

    assert lines[0][2] == Decimal("20.50")
    assert total == Decimal("20.50")


def test_calculate_order_rejects_missing_product() -> None:
    with pytest.raises(ValidationError):
        calculate_order([OrderItemInput(uuid.uuid4(), 1)], [])
