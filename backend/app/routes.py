import base64
import binascii
import os
import re
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db
from .models import Issue, IssueStatusHistory
from .schemas import IssueCreate, IssueRead, IssueStatusUpdate, IssueStatusHistoryRead
from .services import assess_safety_risk, classify_issue, suggest_category, suggest_department, suggest_priority

router = APIRouter(prefix="/issues", tags=["issues"])
IMAGE_PATTERN = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$")

def validate_image_data(image_data: str) -> bool:
    match = IMAGE_PATTERN.fullmatch(image_data)
    if not match:
        return False
    mime_type, encoded = match.groups()
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return False
    if mime_type == "png":
        return image_bytes.startswith(b"\\x89PNG\\r\\n\\x1a\\n")
    if mime_type == "jpeg":
        return image_bytes.startswith(b"\\xff\\xd8\\xff")
    if mime_type == "webp":
        return len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP"
    return False

def require_staff(x_staff_key: str | None = Header(default=None)):
    expected = os.getenv("STAFF_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Staff updates are disabled until STAFF_API_KEY is configured in the backend environment.")
    if not x_staff_key or x_staff_key != expected:
        raise HTTPException(status_code=401, detail="A valid staff access key is required.")

@router.post("/staff/verify", dependencies=[Depends(require_staff)])
def verify_staff_key():
    return {"authorized": True}

@router.get("", response_model=list[IssueRead])
def list_issues(search: str | None = Query(default=None, max_length=180), db: Session = Depends(get_db)):
    items = db.scalars(select(Issue).order_by(Issue.created_at.desc())).all()
    if search:
        term = search.casefold()
        items = [i for i in items if term in " ".join([i.title, i.description, i.category, i.location, i.status]).casefold()]
    return items

@router.post("", response_model=IssueRead, status_code=201)
def create_issue(payload: IssueCreate, db: Session = Depends(get_db)):
    if payload.image_data and not validate_image_data(payload.image_data):
        raise HTTPException(status_code=422, detail="Image must be PNG, JPEG or WEBP.")
    category, confidence = classify_issue(payload.title, payload.description)
    if payload.category != "Other":
        category = payload.category
    elif confidence < 0.30:
        category = "Other"
    risk_score, risk_level, risk_reasons = assess_safety_risk(payload.title, payload.description)
    issue = Issue(
        title=payload.title.strip(), description=payload.description.strip(),
        location=payload.location.strip(), category=category,
        priority=payload.priority or suggest_priority(payload.title, payload.description),
        status="Submitted", department=suggest_department(category),
        image_data=payload.image_data, classification_confidence=round(confidence, 4),
        risk_score=risk_score, risk_level=risk_level, risk_reasons=risk_reasons,
    )
    db.add(issue)
    db.flush()
    db.add(IssueStatusHistory(issue_id=issue.id, old_status=None, new_status="Submitted", changed_by="system"))
    db.commit()
    db.refresh(issue)
    return issue

@router.get("/resolved", response_model=list[IssueRead], dependencies=[Depends(require_staff)])
def list_resolved_issues(db: Session = Depends(get_db)):
    """Return resolved/closed reports for staff review; requires the staff key."""
    return db.scalars(
        select(Issue)
        .where(Issue.status.in_(["Resolved", "Closed"]))
        .order_by(Issue.created_at.desc())
    ).all()

@router.patch("/{issue_id}/status", response_model=IssueRead, dependencies=[Depends(require_staff)])
def update_status(issue_id: int, payload: IssueStatusUpdate, db: Session = Depends(get_db)):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.status != payload.status:
        db.add(IssueStatusHistory(issue_id=issue.id, old_status=issue.status, new_status=payload.status, changed_by="staff-key"))
        issue.status = payload.status
        db.commit()
    db.refresh(issue)
    return issue


@router.get("/{issue_id}/history", response_model=list[IssueStatusHistoryRead], dependencies=[Depends(require_staff)])
def get_issue_history(issue_id: int, db: Session = Depends(get_db)):
    if db.get(Issue, issue_id) is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return db.scalars(
        select(IssueStatusHistory)
        .where(IssueStatusHistory.issue_id == issue_id)
        .order_by(IssueStatusHistory.changed_at.asc(), IssueStatusHistory.id.asc())
    ).all()
