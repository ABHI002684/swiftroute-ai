
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DeliveryStatus = Literal[
    "pending",
    "assigned",
    "picked_up",
    "in_transit",
    "delivered",
    "delayed",
    "failed",
    "cancelled",
]

DeliveryPriority = Literal[
    "low",
    "normal",
    "high",
    "urgent",
]


class DeliveryCreate(BaseModel):
    tracking_number: str = Field(min_length=2, max_length=50)
    customer_name: str = Field(min_length=2, max_length=100)
    customer_phone: str | None = Field(default=None, max_length=20)

    city: str = Field(min_length=2, max_length=50)

    pickup_address: str = Field(min_length=3, max_length=255)
    delivery_address: str = Field(min_length=3, max_length=255)

    priority: DeliveryPriority = "normal"

    assigned_employee_id: int | None = None

    scheduled_delivery: datetime | None = None


class DeliveryUpdate(BaseModel):
    status: DeliveryStatus = "pending"
    priority: DeliveryPriority = "normal"

    assigned_employee_id: int | None = None

    scheduled_delivery: datetime | None = None


class DeliveryResponse(BaseModel):
    id: int
    tracking_number: str

    customer_name: str
    customer_phone: str | None

    city: str
    pickup_address: str
    delivery_address: str

    status: DeliveryStatus
    priority: DeliveryPriority

    assigned_employee_id: int | None

    scheduled_delivery: datetime | None
    delivered_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
