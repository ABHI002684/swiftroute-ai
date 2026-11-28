
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.delivery import Delivery
from app.models.employee import Employee
from app.schemas.delivery import (
    DeliveryCreate,
    DeliveryUpdate,
    DeliveryResponse,
)

router = APIRouter()


def validate_employee_assignment(
    db: Session,
    employee_id: int,
    delivery_city: str,
):
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Assigned employee not found",
        )

    if not employee.is_active:
        raise HTTPException(
            status_code=409,
            detail="Cannot assign delivery to an inactive employee",
        )

    if employee.city.casefold() != delivery_city.casefold():
        raise HTTPException(
            status_code=409,
            detail="Employee and delivery must belong to the same city",
        )

    return employee


@router.post(
    "",
    response_model=DeliveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery(
    delivery_data: DeliveryCreate,
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(Delivery).where(
            Delivery.tracking_number == delivery_data.tracking_number
        )
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Tracking number already exists",
        )

    data = delivery_data.model_dump()

    employee_id = data.get("assigned_employee_id")

    if employee_id is not None:
        validate_employee_assignment(
            db,
            employee_id,
            data["city"],
        )
        data["status"] = "assigned"
    else:
        data["status"] = "pending"

    delivery = Delivery(**data)

    try:
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create delivery due to a data conflict",
        )

    return delivery


@router.get("", response_model=list[DeliveryResponse])
def list_deliveries(
    city: str | None = None,
    delivery_status: str | None = Query(
        default=None,
        alias="status",
    ),
    priority: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    statement = select(Delivery)

    if city:
        statement = statement.where(
            Delivery.city.ilike(city)
        )

    if delivery_status:
        statement = statement.where(
            Delivery.status == delivery_status
        )

    if priority:
        statement = statement.where(
            Delivery.priority == priority
        )

    statement = (
        statement
        .order_by(Delivery.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


@router.get("/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
):
    delivery = db.get(Delivery, delivery_id)

    if delivery is None:
        raise HTTPException(
            status_code=404,
            detail="Delivery not found",
        )

    return delivery


@router.patch("/{delivery_id}", response_model=DeliveryResponse)
def update_delivery(
    delivery_id: int,
    delivery_data: DeliveryUpdate,
    db: Session = Depends(get_db),
):
    delivery = db.get(Delivery, delivery_id)

    if delivery is None:
        raise HTTPException(
            status_code=404,
            detail="Delivery not found",
        )

    if delivery.status in {"delivered", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail="Delivered or cancelled deliveries cannot be modified",
        )

    updates = delivery_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    new_employee_id = updates.get(
        "assigned_employee_id",
        delivery.assigned_employee_id,
    )

    if new_employee_id is not None:
        validate_employee_assignment(
            db,
            new_employee_id,
            delivery.city,
        )

    new_status = updates.get("status", delivery.status)

    allowed_transitions = {
        "pending": {"assigned", "cancelled"},
        "assigned": {"picked_up", "cancelled"},
        "picked_up": {"in_transit", "delayed", "failed", "cancelled"},
        "in_transit": {"delivered", "delayed", "failed", "cancelled"},
        "delayed": {"in_transit", "delivered", "failed", "cancelled"},
        "failed": {"assigned", "cancelled"},
    }

    if "status" in updates:
        allowed = allowed_transitions.get(delivery.status, set())

        if new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Invalid status transition: "
                    f"{delivery.status} -> {new_status}"
                ),
            )

    for field, value in updates.items():
        setattr(delivery, field, value)

    if "assigned_employee_id" in updates and "status" not in updates:
        if new_employee_id is not None and delivery.status == "pending":
            delivery.status = "assigned"
        elif new_employee_id is None and delivery.status == "assigned":
            delivery.status = "pending"

    if delivery.status == "delivered":
        delivery.delivered_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(delivery)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not update delivery due to a data conflict",
        )

    return delivery


@router.delete("/{delivery_id}")
def cancel_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
):
    delivery = db.get(Delivery, delivery_id)

    if delivery is None:
        raise HTTPException(
            status_code=404,
            detail="Delivery not found",
        )

    if delivery.status in {"delivered", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail="Delivery is already completed or cancelled",
        )

    delivery.status = "cancelled"

    db.commit()

    return {
        "message": "Delivery cancelled successfully",
        "delivery_id": delivery.id,
        "status": delivery.status,
    }
