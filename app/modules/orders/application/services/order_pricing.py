from decimal import Decimal

from app.modules.catalog.infrastructure.models.catalog import ProductModel
from app.modules.orders.application.dto.orders import OrderItemInput
from app.shared.domain.exceptions import ValidationError


def calculate_order(
    requested_items: list[OrderItemInput], products: list[ProductModel]
) -> tuple[list[tuple[ProductModel, int, Decimal]], Decimal]:
    if not requested_items:
        raise ValidationError("Order must contain at least one item")
    product_map = {product.id: product for product in products}
    lines: list[tuple[ProductModel, int, Decimal]] = []
    total = Decimal("0.00")
    for requested in requested_items:
        if requested.quantity < 1 or requested.quantity > 999:
            raise ValidationError("Item quantity must be between 1 and 999")
        product = product_map.get(requested.product_id)
        if product is None:
            raise ValidationError(f"Product {requested.product_id} is unavailable")
        line_total = product.price * requested.quantity
        lines.append((product, requested.quantity, line_total))
        total += line_total
    return lines, total
