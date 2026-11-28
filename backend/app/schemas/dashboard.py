
from pydantic import BaseModel


class DashboardOverview(BaseModel):
    total_deliveries: int
    delivered: int
    pending: int
    in_transit: int
    delayed: int
    failed: int
    active_employees: int
    completion_rate: float
    overdue_deliveries: int
    deliveries_requiring_attention: int
