from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardDTO:
    visits: int
    product_views: int
    orders: int
    completed_orders: int
    conversion_rate: float
