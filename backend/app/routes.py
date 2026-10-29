from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db
from .models import Issue
from .schemas import IssueCreate, IssueRead, IssueStatusUpdate
from .services import suggest_category, suggest_department, suggest_priority

router = APIRouter(prefix="/issues", tags=["issues"])

@router.get("", response_model=list[IssueRead])
def list_issues(search: str | None = Query(default=None, max_length=180), db: Session = Depends(get_db)):
    items = db.scalars(select(Issue).order_by(Issue.created_at.desc())).all()
    if search:
        term = search.casefold()
        items = [i for i in items if term in " ".join([i.title, i.description, i.category, i.location, i.status]).casefold()]
    return items

@router.post("", response_model=IssueRead, status_code=201)
def create_issue(payload: IssueCreate, db: Session = Depends(get_db)):
    category = payload.category
    if category == "Other":
        category = suggest_category(payload.title, payload.description)
    issue = Issue(
        title=payload.title.strip(), description=payload.description.strip(),
        location=payload.location.strip(), category=category,
        priority=payload.priority or suggest_priority(payload.title, payload.description),
        status="Submitted", department=suggest_department(category),
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue

@router.patch("/{issue_id}/status", response_model=IssueRead)
def update_status(issue_id: int, payload: IssueStatusUpdate, db: Session = Depends(get_db)):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = payload.status
    db.commit()
    db.refresh(issue)
    return issue
