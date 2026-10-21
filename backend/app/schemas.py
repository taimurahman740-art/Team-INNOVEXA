from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Category = Literal["Facility", "Electrical", "Plumbing", "Cleaning", "Safety", "Other"]
Priority = Literal["Low", "Medium", "High"]
Status = Literal["Submitted", "In Progress", "Resolved", "Closed"]

class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=3000)
    location: str = Field(min_length=2, max_length=180)
    category: Category = "Other"
    priority: Priority | None = None

class IssueStatusUpdate(BaseModel):
    status: Status

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
    created_at: datetime
