from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Category = Literal["Facility", "Electrical", "Plumbing", "Cleaning", "Safety", "Other"]
Priority = Literal["Low", "Medium", "High"]
Status = Literal["Submitted", "In Progress", "Resolved", "Closed"]
StaffRole = Literal["admin", "staff"]
Department = Literal["Electrical Maintenance", "Plumbing Maintenance", "Cleaning Services", "Campus Safety", "Facilities Maintenance", "Campus Administration"]

class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=3000)
    location: str = Field(min_length=2, max_length=180)
    category: Category = "Other"
    priority: Priority | None = None
    image_data: str | None = Field(default=None, max_length=2_800_000)
class ImageClassificationRequest(BaseModel):
    image_data: str = Field(min_length=30, max_length=2_800_000)
class IssueStatusUpdate(BaseModel):
    status: Status
class IssueAssignmentUpdate(BaseModel):
    staff_user_id: int | None = Field(default=None, ge=1)
class StaffLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)
class StaffBootstrap(BaseModel):
    bootstrap_key: str = Field(min_length=1, max_length=256)
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=200)
    department: Department = "Campus Administration"
class StaffUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=200)
    department: Department
    role: StaffRole = "staff"
class StaffUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    department: str
    role: str
    is_active: bool
    created_at: datetime
class StaffTokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: StaffUserRead
class StaffSetupStatus(BaseModel):
    setup_available: bool
class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    location: str
    department: str | None = None
    assigned_staff_id: int | None = None
    image_data: str | None = None
    classification_confidence: float | None = None
    risk_score: int = 0
    risk_level: str = "Low"
    risk_reasons: list[str] = Field(default_factory=list)
    tracking_code: str | None = None
    created_at: datetime
class IssuePublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    category: str
    priority: str
    status: str
    department: str | None = None
    created_at: datetime
class IssueStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    issue_id: int
    old_status: str | None = None
    new_status: str
    changed_at: datetime
    changed_by: str
class IssueTrackingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    old_status: str | None = None
    new_status: str
    changed_at: datetime
class IssueTrackingRead(BaseModel):
    tracking_code: str
    title: str
    category: str
    priority: str
    status: str
    department: str | None = None
    created_at: datetime
    history: list[IssueTrackingEventRead] = Field(default_factory=list)
