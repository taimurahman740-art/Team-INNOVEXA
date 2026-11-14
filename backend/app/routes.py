import base64
import binascii
import hmac
import os
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .auth import TOKEN_LIFETIME_SECONDS, create_access_token, get_current_staff, hash_password, require_admin, verify_password
from .database import get_db
from .models import Issue, IssueStatusHistory, StaffUser
from .schemas import (
    IssueCreate, ImageClassificationRequest, IssueRead, IssuePublicRead,
    IssueStatusUpdate, IssueStatusHistoryRead, IssueTrackingRead,
    IssueAssignmentUpdate, StaffLogin, StaffBootstrap, StaffUserCreate,
    StaffUserRead, StaffTokenRead, StaffSetupStatus,
)
from .image_recognition import classify_campus_image
from .services import assess_safety_risk, classify_issue, suggest_category, suggest_department, suggest_priority

router = APIRouter(prefix="/issues", tags=["issues"])
IMAGE_PATTERN = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


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
        return image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "jpeg":
        return image_bytes.startswith(b"\xff\xd8\xff")
    if mime_type == "webp":
        return len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP"
    return False


def _session_response(user: StaffUser) -> dict:
    return {"access_token": create_access_token(user), "token_type": "bearer", "expires_in": TOKEN_LIFETIME_SECONDS, "user": user}


@router.get("/staff/setup-status", response_model=StaffSetupStatus)
def staff_setup_status(db: Session = Depends(get_db)):
    count = db.scalar(select(func.count(StaffUser.id))) or 0
    return {"setup_available": count == 0 and bool(os.getenv("STAFF_BOOTSTRAP_KEY"))}


@router.post("/staff/bootstrap", response_model=StaffTokenRead, status_code=201)
def bootstrap_first_admin(payload: StaffBootstrap, db: Session = Depends(get_db)):
    expected = os.getenv("STAFF_BOOTSTRAP_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Initial staff setup is disabled. Configure STAFF_BOOTSTRAP_KEY first.")
    if not hmac.compare_digest(payload.bootstrap_key, expected):
        raise HTTPException(status_code=401, detail="Invalid initial setup key.")
    if (db.scalar(select(func.count(StaffUser.id))) or 0) != 0:
        raise HTTPException(status_code=409, detail="The first administrator has already been created.")
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    user = StaffUser(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password), department=payload.department, role="admin", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _session_response(user)


@router.post("/staff/login", response_model=StaffTokenRead)
def staff_login(payload: StaffLogin, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalar(select(StaffUser).where(StaffUser.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return _session_response(user)


@router.get("/staff/me", response_model=StaffUserRead)
def staff_me(user: StaffUser = Depends(get_current_staff)):
    return user


@router.post("/staff/users", response_model=StaffUserRead, status_code=201)
def create_staff_user(payload: StaffUserCreate, admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if db.scalar(select(StaffUser).where(StaffUser.email == email)):
        raise HTTPException(status_code=409, detail="A staff account with this email already exists.")
    user = StaffUser(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password), department=payload.department, role=payload.role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/staff/users", response_model=list[StaffUserRead])
def list_staff_users(admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(StaffUser).order_by(StaffUser.department, StaffUser.full_name)).all()


@router.get("", response_model=list[IssuePublicRead])
def list_issues(search: str | None = Query(default=None, max_length=180), db: Session = Depends(get_db)):
    items = db.scalars(select(Issue).order_by(Issue.created_at.desc())).all()
    if search:
        term = search.casefold()
        items = [i for i in items if term in " ".join([i.title, i.category, i.status, i.department or ""]).casefold()]
    return items


@router.get("/track/{tracking_code}", response_model=IssueTrackingRead)
def track_issue(tracking_code: str, db: Session = Depends(get_db)):
    code = tracking_code.strip().upper()
    issue = db.scalar(select(Issue).where(Issue.tracking_code == code))
    if issue is None:
        raise HTTPException(status_code=404, detail="No report found for that tracking code.")
    history = db.scalars(select(IssueStatusHistory).where(IssueStatusHistory.issue_id == issue.id).order_by(IssueStatusHistory.changed_at.asc(), IssueStatusHistory.id.asc())).all()
    return {"tracking_code":issue.tracking_code,"title":issue.title,"category":issue.category,"priority":issue.priority,"status":issue.status,"department":issue.department,"created_at":issue.created_at,"history":history}


def _department_scope(statement, user: StaffUser):
    if user.role == "admin":
        return statement
    return statement.where(
        Issue.department == user.department,
        (Issue.assigned_staff_id.is_(None)) | (Issue.assigned_staff_id == user.id),
    )


@router.get("/staff", response_model=list[IssueRead])
def list_staff_issues(user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    statement = select(Issue).order_by(Issue.created_at.desc())
    return db.scalars(_department_scope(statement, user)).all()


@router.get("/resolved", response_model=list[IssueRead])
def list_resolved_issues(user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    statement = select(Issue).where(Issue.status.in_(["Resolved","Closed"])).order_by(Issue.created_at.desc())
    return db.scalars(_department_scope(statement, user)).all()


def _can_work(issue: Issue, user: StaffUser) -> bool:
    return user.role == "admin" or (issue.department == user.department and issue.assigned_staff_id in (None, user.id))


@router.patch("/{issue_id}/status", response_model=IssueRead)
def update_status(issue_id: int, payload: IssueStatusUpdate, user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not _can_work(issue, user):
        raise HTTPException(status_code=403, detail="This report is assigned to another department or staff member.")
    if issue.status != payload.status:
        db.add(IssueStatusHistory(issue_id=issue.id, old_status=issue.status, new_status=payload.status, changed_by=user.email[:80]))
        issue.status = payload.status
        db.commit()
    db.refresh(issue)
    return issue


@router.patch("/{issue_id}/assignment", response_model=IssueRead)
def assign_issue(issue_id: int, payload: IssueAssignmentUpdate, admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if payload.staff_user_id is None:
        issue.assigned_staff_id = None
    else:
        member = db.get(StaffUser, payload.staff_user_id)
        if member is None or not member.is_active:
            raise HTTPException(status_code=404, detail="Active staff account not found.")
        if member.department != issue.department:
            raise HTTPException(status_code=422, detail="Staff member must belong to the report's assigned department.")
        issue.assigned_staff_id = member.id
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/{issue_id}/history", response_model=list[IssueStatusHistoryRead])
def get_issue_history(issue_id: int, user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not _can_work(issue, user):
        raise HTTPException(status_code=403, detail="This report is outside your assigned work.")
    return db.scalars(select(IssueStatusHistory).where(IssueStatusHistory.issue_id == issue_id).order_by(IssueStatusHistory.changed_at.asc(), IssueStatusHistory.id.asc())).all()


@router.post("", response_model=IssueRead, status_code=201)
def create_issue(payload: IssueCreate, db: Session = Depends(get_db)):
    if payload.image_data and not validate_image_data(payload.image_data):
        raise HTTPException(status_code=422, detail="Image must be PNG, JPEG or WEBP.")

    _, confidence = classify_issue(payload.title, payload.description)
    category = (
        payload.category
        if payload.category != "Other"
        else suggest_category(payload.title, payload.description)
    )

    risk_score, risk_level, risk_reasons = assess_safety_risk(payload.title, payload.description)
    suggested_priority = suggest_priority(payload.title, payload.description)
    final_priority = "High" if risk_score >= 5 else (payload.priority or suggested_priority)
    issue = Issue(title=payload.title.strip(), description=payload.description.strip(), location=payload.location.strip(), category=category, priority=final_priority, status="Submitted", department=suggest_department(category), image_data=payload.image_data, classification_confidence=round(confidence,4), risk_score=risk_score, risk_level=risk_level, risk_reasons=risk_reasons)
    db.add(issue)
    db.flush()
    db.add(IssueStatusHistory(issue_id=issue.id, old_status=None, new_status="Submitted", changed_by="system"))
    db.commit()
    db.refresh(issue)
    return issue


@router.post("/image-classification")
def image_classification(payload: ImageClassificationRequest):
    if not validate_image_data(payload.image_data):
        raise HTTPException(status_code=422, detail="Image must be a valid PNG, JPEG or WEBP.")
    token = os.getenv("HF_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="Image recognition is not configured yet. Add HF_TOKEN to the backend environment.")
    match = IMAGE_PATTERN.fullmatch(payload.image_data)
    image_bytes = base64.b64decode(match.group(2), validate=True)
    try:
        return classify_campus_image(image_bytes, token, os.getenv("HF_IMAGE_MODEL", "openai/clip-vit-large-patch14"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Image recognition is temporarily unavailable. You can still choose a category manually.") from exc
