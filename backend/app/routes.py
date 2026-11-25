import base64
from datetime import datetime, timezone
import binascii
import hmac
import os
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .auth import TOKEN_LIFETIME_SECONDS, create_access_token, get_current_staff, hash_password, require_admin, verify_password
from .database import get_db
from .models import Escalation, Issue, IssueStatusHistory, ResponseTarget, StaffUser
from .schemas import (
    IssueCreate, ImageClassificationRequest, IssueRead, IssuePublicRead,
    IssueStatusUpdate, IssueStatusHistoryRead, IssueTrackingRead,
    IssueAssignmentUpdate, DuplicateReview, StaffLogin, StaffBootstrap, StaffUserCreate,
    StaffUserRead, StaffTokenRead, StaffSetupStatus,
    EscalationRead, ResponseTargetRead, ResponseTargetsUpdate,
)
from .image_recognition import classify_campus_image
from .priority_model import predict_priority
from .duplicates import OPEN_STATUSES, find_possible_duplicates
from .analytics import response_time_stats
from .escalation import run_check
from .services import assess_safety_risk, choose_category, classify_issue, merge_image_hazard_risk, routing_reason, suggest_department, suggest_priority

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
    run_check(db)  # throttled overdue/escalation check (no scheduler on Render's free tier)
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
    changed = False
    if issue.status != payload.status:
        db.add(IssueStatusHistory(issue_id=issue.id, old_status=issue.status, new_status=payload.status, changed_by=user.email[:80]))
        issue.status = payload.status
        changed = True
    if payload.resolution_note is not None:
        issue.resolution_note = payload.resolution_note.strip() or None
        changed = True
    if changed:
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


@router.get("/response-targets", response_model=list[ResponseTargetRead])
def list_response_targets(user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(db.query(ResponseTarget).all(), key=lambda t: order.get(t.priority, 9))


@router.patch("/response-targets", response_model=list[ResponseTargetRead])
def update_response_targets(payload: ResponseTargetsUpdate, admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    if len({t.priority for t in payload.targets}) != len(payload.targets):
        raise HTTPException(status_code=422, detail="Each priority can appear only once.")
    for t in payload.targets:
        row = db.get(ResponseTarget, t.priority) or ResponseTarget(priority=t.priority)
        row.start_within_minutes, row.resolve_within_minutes, row.auto_escalate = t.start_within_minutes, t.resolve_within_minutes, t.auto_escalate
        row.updated_at, row.updated_by = datetime.now(timezone.utc), admin.email[:80]
        db.add(row)
    db.commit()
    run_check(db, force=True)
    return list_response_targets(admin, db)


def _escalation_read(e: Escalation, issue: Issue) -> dict:
    return {**{c: getattr(e, c) for c in ("id", "issue_id", "kind", "priority", "target_minutes", "reason", "escalated_to", "created_at", "acknowledged_at", "acknowledged_by")},
            "issue_title": issue.title, "issue_status": issue.status, "issue_department": issue.department, "issue_location": issue.location}


@router.get("/escalations", response_model=list[EscalationRead])
def list_escalations(user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    """Admins see every escalation; staff see those for their department."""
    run_check(db)
    query = db.query(Escalation, Issue).join(Issue, Issue.id == Escalation.issue_id)
    if user.role != "admin":
        query = query.filter(Issue.department == user.department)
    return [_escalation_read(e, i) for e, i in query.order_by(Escalation.created_at.desc()).limit(300).all()]


@router.post("/escalations/check")
def check_escalations(admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    return {"created": run_check(db, force=True)}


@router.post("/escalations/{escalation_id}/acknowledge", response_model=EscalationRead)
def acknowledge_escalation(escalation_id: int, user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    escalation = db.get(Escalation, escalation_id)
    if escalation is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    issue = db.get(Issue, escalation.issue_id)
    if user.role != "admin" and issue.department != user.department:
        raise HTTPException(status_code=403, detail="This escalation is outside your department.")
    if escalation.acknowledged_at is None:
        escalation.acknowledged_at, escalation.acknowledged_by = datetime.now(timezone.utc), user.email[:80]
        db.commit()
    return _escalation_read(escalation, issue)


@router.get("/analytics/response-times")
def analytics_response_times(admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    """Real response and resolution times from status history (administrators only)."""
    issues = [{"id": i.id, "created_at": i.created_at, "department": i.department, "priority": i.priority} for i in db.scalars(select(Issue)).all()]
    history = [{"issue_id": h.issue_id, "new_status": h.new_status, "changed_at": h.changed_at} for h in db.scalars(select(IssueStatusHistory)).all()]
    return response_time_stats(issues, history)


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

    analysis = payload.image_analysis.model_dump() if (payload.image_data and payload.image_analysis) else None
    user_title = (payload.title or "").strip()
    user_description = (payload.description or "").strip()
    has_user_text = len(user_title) >= 3 and len(user_description) >= 5
    title, description = user_title, user_description
    if not has_user_text:
        # Image-only report: fill the gaps from the photo suggestion, or ask for more.
        if analysis is None or analysis.get("needs_more_info"):
            raise HTTPException(status_code=422, detail="The photo alone is not enough to identify the problem. Please add a short title and description.")
        if len(title) < 3:
            title = (analysis.get("suggested_title") or f"{analysis['category']} issue (photo report)")[:120]
        if len(description) < 5:
            description = analysis.get("suggested_description") or "Photo report submitted without a description."

    _, text_confidence = classify_issue(title, description)
    if payload.category not in (None, "Other"):
        category, confidence, source, fusion = payload.category, text_confidence, "user", {}
    else:
        category, confidence, source, fusion = choose_category(title, description, has_user_text, analysis)

    # Keyword risk uses only what the reporter wrote, so suggested text cannot count twice.
    risk_score, _, risk_reasons = assess_safety_risk(user_title, user_description)
    risk_score, risk_level, risk_reasons = merge_image_hazard_risk(risk_score, risk_reasons, analysis)
    rule_priority = suggest_priority(user_title, user_description) if has_user_text else ("High" if risk_score >= 5 else "Medium")
    prediction = predict_priority(category, title, description, payload.location, risk_score, rule_priority)
    # Safety floor first; otherwise a priority chosen by the reporter, otherwise the model.
    final_priority = "High" if risk_score >= 5 else (payload.priority or prediction["final"])
    prediction["reporter_choice"] = payload.priority
    ai_analysis = {
        "priority": prediction,
        "image_only": not has_user_text,
        "category_source": source,
        "routing_reason": routing_reason(category, source),
        **fusion,
    }
    department = suggest_department(category)
    ai_analysis["duplicates"] = _duplicate_check(db, {"title": title, "description": description, "department": department, "building": (payload.building or "").strip() or None, "image_data": payload.image_data})
    if analysis:
        ai_analysis["image"] = {k: analysis.get(k) for k in ("category", "score", "category_scores", "hazard", "model")}
    issue = Issue(title=title, description=description, location=payload.location.strip(), building=(payload.building or "").strip() or None, equipment=(payload.equipment or "").strip() or None, category=category, priority=final_priority, status="Submitted", department=department, image_data=payload.image_data, classification_confidence=round(confidence, 4), risk_score=risk_score, risk_level=risk_level, risk_reasons=risk_reasons, ai_analysis=ai_analysis)
    db.add(issue)
    db.flush()
    db.add(IssueStatusHistory(issue_id=issue.id, old_status=None, new_status="Submitted", changed_by="system"))
    db.commit()
    db.refresh(issue)
    return issue


def _duplicate_check(db: Session, new: dict) -> dict:
    """Flag similar open reports for staff review. Never blocks or rejects the new report."""
    try:
        recent = db.scalars(select(Issue).where(Issue.status.in_(OPEN_STATUSES)).order_by(Issue.created_at.desc()).limit(50)).all()
        candidates = [{"id": i.id, "title": i.title, "description": i.description, "department": i.department, "building": i.building, "image_data": i.image_data, "status": i.status} for i in recent]
        return {"method": "tfidf_text_cosine+image_feature_cosine", "matches": find_possible_duplicates(new, candidates), "review": None}
    except Exception as exc:  # the check is advisory; a failure must not lose the report
        return {"method": "unavailable", "matches": [], "review": None, "error": type(exc).__name__}


@router.patch("/{issue_id}/duplicate-review", response_model=IssueRead)
def review_duplicate(issue_id: int, payload: DuplicateReview, user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    """Staff confirm or dismiss a possible duplicate. Nothing is merged or closed automatically."""
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not _can_work(issue, user):
        raise HTTPException(status_code=403, detail="This report is outside your assigned work.")
    if payload.decision == "duplicate":
        if payload.duplicate_of is None or payload.duplicate_of == issue.id or db.get(Issue, payload.duplicate_of) is None:
            raise HTTPException(status_code=422, detail="Choose the existing report this one duplicates.")
    analysis = dict(issue.ai_analysis or {})
    duplicates = dict(analysis.get("duplicates") or {"method": "manual", "matches": []})
    duplicates["review"] = {"decision": payload.decision, "duplicate_of": payload.duplicate_of if payload.decision == "duplicate" else None,
                            "reviewed_by": user.email[:80], "reviewed_at": datetime.now(timezone.utc).isoformat()}
    analysis["duplicates"] = duplicates
    issue.ai_analysis = analysis  # reassign so SQLAlchemy saves the JSON change
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
