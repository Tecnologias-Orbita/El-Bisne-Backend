import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OrderItemInput:
    product_id: uuid.UUID
    quantity: int


@dataclass(frozen=True)
class OrderDTO:
    id: uuid.UUID
    order_number: str
    status: str
    currency: str
    subtotal: Decimal
    total: Decimal


@dataclass(frozen=True)
class OrderItemDTO:
    id: uuid.UUID
    product_id: uuid.UUID | None
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass(frozen=True)
class OrderDetailDTO(OrderDTO):
    customer_name: str
    customer_email: str | None
    customer_phone: str | None
    notes: str | None
    items: list[OrderItemDTO]
