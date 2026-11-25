from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["Facility", "Electrical", "Plumbing", "HVAC", "IT", "Cleaning", "Safety", "Other"]
HazardKey = Literal["exposed_wiring", "water_pooling", "structural_crack", "broken_glass"]
Priority = Literal["Low", "Medium", "High"]
Status = Literal["Submitted", "In Progress", "Resolved", "Closed"]
StaffRole = Literal["admin", "staff"]
Department = Literal["Electrical Maintenance", "Plumbing Maintenance", "Cleaning Services", "Campus Safety", "Facilities Maintenance", "HVAC Maintenance", "IT Infrastructure", "Campus Administration"]

class ImageHazard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: HazardKey
    label: str = Field(max_length=80)
    score: float = Field(ge=0, le=1)
    risk_points: int = Field(default=0, ge=0, le=5)


class ImageAnalysis(BaseModel):
    """Result of /issues/image-classification, sent back with the report.

    It is advisory: it can raise risk or suggest a category, and the reporter can
    edit everything it suggests. It can never lower the keyword safety risk.
    """
    model_config = ConfigDict(extra="ignore")
    category: Category
    score: float = Field(ge=0, le=1)
    category_scores: dict[Category, float] | None = None
    hazard: ImageHazard | None = None
    needs_more_info: bool = False
    suggested_title: str | None = Field(default=None, max_length=120)
    suggested_description: str | None = Field(default=None, max_length=600)
    model: str | None = Field(default=None, max_length=120)


class IssueCreate(BaseModel):
    # Title and description may be left empty when a photo is attached (image-only report).
    title: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=3000)
    location: str = Field(min_length=2, max_length=180)
    building: str | None = Field(default=None, max_length=80)
    floor: str | None = Field(default=None, max_length=20)
    room: str | None = Field(default=None, max_length=40)
    # None or "Other" means "let INNOVEXA decide".
    category: Category | None = None
    priority: Priority | None = None
    image_data: str | None = Field(default=None, max_length=2_800_000)
    image_analysis: ImageAnalysis | None = None

    @model_validator(mode="after")
    def text_required_without_photo(self):
        if not self.image_data:
            if len((self.title or "").strip()) < 3:
                raise ValueError("Enter a title of at least 3 characters, or attach a photo.")
            if len((self.description or "").strip()) < 5:
                raise ValueError("Enter a description of at least 5 characters, or attach a photo.")
        return self
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
    building: str | None = None
    ai_analysis: dict | None = None
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
