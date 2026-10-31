import os
import re
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db
from .models import Issue
from .schemas import IssueCreate, IssueRead, IssueStatusUpdate
from .services import classify_issue, suggest_category, suggest_department, suggest_priority

router = APIRouter(prefix="/issues", tags=["issues"])
IMAGE_PATTERN = re.compile(r"^data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$")

def require_staff(x_staff_key: str | None = Header(default=None)):
    expected = os.getenv("STAFF_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Staff updates are disabled until STAFF_API_KEY is configured in the backend environment.")
    if not x_staff_key or x_staff_key != expected:
        raise HTTPException(status_code=401, detail="A valid staff access key is required.")

@router.get("", response_model=list[IssueRead])
def list_issues(search: str | None = Query(default=None, max_length=180), db: Session = Depends(get_db)):
    items = db.scalars(select(Issue).order_by(Issue.created_at.desc())).all()
    if search:
        term = search.casefold()
        items = [i for i in items if term in " ".join([i.title, i.description, i.category, i.location, i.status]).casefold()]
    return items

@router.post("", response_model=IssueRead, status_code=201)
def create_issue(payload: IssueCreate, db: Session = Depends(get_db)):
    if payload.image_data and not IMAGE_PATTERN.fullmatch(payload.image_data):
        raise HTTPException(status_code=422, detail="Image must be PNG, JPEG or WEBP.")
    category, confidence = classify_issue(payload.title, payload.description)
    if payload.category != "Other":
        category = payload.category
    elif confidence < 0.30:
        category = "Other"
    issue = Issue(
        title=payload.title.strip(), description=payload.description.strip(),
        location=payload.location.strip(), category=category,
        priority=payload.priority or suggest_priority(payload.title, payload.description),
        status="Submitted", department=suggest_department(category),
        image_data=payload.image_data, classification_confidence=round(confidence, 4),
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue

@router.patch("/{issue_id}/status", response_model=IssueRead, dependencies=[Depends(require_staff)])
def update_status(issue_id: int, payload: IssueStatusUpdate, db: Session = Depends(get_db)):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = payload.status
    db.commit()
    db.refresh(issue)
    return issue
