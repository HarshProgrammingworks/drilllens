from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=200)
    remember: bool = False


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=1, max_length=200)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=8, max_length=200)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class UserOut(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    email: EmailStr | None = None


class UserCreateAdmin(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    full_name: str
    role: str = "VIEWER"
    is_active: bool = True


class WellIn(BaseModel):
    well_id: str = Field(min_length=1, max_length=64)
    well_name: str
    field: str
    operator: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    status: str = "PLANNED"
    current_depth: float | None = None
    formation: str | None = None
    spud_date: date | None = None
    completion_date: date | None = None
    well_type: str = "DEVELOPMENT"
    trajectory_type: str = "VERTICAL"
    current_operation: str | None = None
    simulate_sensors: bool = False


class WellUpdate(BaseModel):
    well_name: str | None = None
    field: str | None = None
    operator: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: str | None = None
    current_depth: float | None = None
    formation: str | None = None
    spud_date: date | None = None
    completion_date: date | None = None
    well_type: str | None = None
    trajectory_type: str | None = None
    current_operation: str | None = None
    simulate_sensors: bool | None = None
    is_archived: bool | None = None


class ReviewIn(BaseModel):
    well_id: UUID | None = None
    alert_id: UUID | None = None
    decision: str
    comment: str | None = None
    risk_category: str | None = None


class ReviewUpdate(BaseModel):
    decision: str | None = None
    comment: str | None = None


class AlertAction(BaseModel):
    note: str | None = None


class ThresholdUpdate(BaseModel):
    low_max: float | None = Field(default=None, ge=0, le=100)
    moderate_max: float | None = Field(default=None, ge=0, le=100)
    high_max: float | None = Field(default=None, ge=0, le=100)
    alert_min_score: float | None = Field(default=None, ge=0, le=100)
    cooldown_minutes: int | None = Field(default=None, ge=1, le=1440)
    torque_rise_pct: float | None = Field(default=None, ge=0, le=200)
    pressure_rise_pct: float | None = Field(default=None, ge=0, le=200)
    flow_change_pct: float | None = Field(default=None, ge=0, le=200)


class AnalyzeRequest(BaseModel):
    well_id: UUID


class DemoScenarioRequest(BaseModel):
    scenario: str


class SimilarityWeights(BaseModel):
    geographic: float = 0.20
    formation: float = 0.25
    depth: float = 0.20
    trajectory: float = 0.15
    event: float = 0.20
