
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    city: str = Field(min_length=2, max_length=50)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, min_length=2, max_length=50)
    is_active: bool | None = None


class EmployeeResponse(BaseModel):
    id: int
    employee_code: str
    name: str
    phone: str | None
    city: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
