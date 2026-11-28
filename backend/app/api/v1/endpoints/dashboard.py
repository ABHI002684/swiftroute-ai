
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.delivery import Delivery
from app.models.employee import Employee
from app.schemas.dashboard import DashboardOverview


router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(
    db: Session = Depends(get_db),
):
    status_counts = dict(
        db.execute(
            select(
                Delivery.status,
                func.count(Delivery.id),
            ).group_by(Delivery.status)
        ).all()
    )

    total_deliveries = sum(status_counts.values())

    delivered = status_counts.get("delivered", 0)
    pending = status_counts.get("pending", 0)
    in_transit = status_counts.get("in_transit", 0)
    delayed = status_counts.get("delayed", 0)
    failed = status_counts.get("failed", 0)

    active_employees = db.scalar(
        select(func.count(Employee.id)).where(
            Employee.is_active.is_(True)
        )
    ) or 0

    now = datetime.now(timezone.utc)

    overdue_condition = (
        Delivery.scheduled_delivery.is_not(None)
        & (Delivery.scheduled_delivery < now)
        & Delivery.status.notin_(
            ["delivered", "cancelled", "failed"]
        )
    )

    overdue_deliveries = db.scalar(
        select(func.count(Delivery.id)).where(
            overdue_condition
        )
    ) or 0

    attention_count = db.scalar(
        select(func.count(Delivery.id)).where(
            or_(
                Delivery.status == "delayed",
                overdue_condition,
            )
        )
    ) or 0

    completion_rate = (
        round((delivered / total_deliveries) * 100, 2)
        if total_deliveries
        else 0.0
    )

    return DashboardOverview(
        total_deliveries=total_deliveries,
        delivered=delivered,
        pending=pending,
        in_transit=in_transit,
        delayed=delayed,
        failed=failed,
        active_employees=active_employees,
        completion_rate=completion_rate,
        overdue_deliveries=overdue_deliveries,
        deliveries_requiring_attention=attention_count,
    )
