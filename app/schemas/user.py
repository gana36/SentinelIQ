import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PreferencesOut(BaseModel):
    risk_tolerance: Literal["low", "medium", "high"]
    alert_sensitivity: float
    sectors: list[str]

    model_config = {"from_attributes": True}


class PreferencesUpdate(BaseModel):
    risk_tolerance: Literal["low", "medium", "high"] | None = None
    alert_sensitivity: float | None = None
    sectors: list[str] | None = None
