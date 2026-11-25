from datetime import datetime, timezone
import secrets
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def generate_tracking_code() -> str:
    """Generate an INNOVEXA tracking code that fits VARCHAR(32)."""
    return "INX-" + secrets.token_hex(14).upper()


class StaffUser(Base):
    __tablename__ = "staff_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="staff")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="Other")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Submitted")
    location: Mapped[str] = mapped_column(String(180), nullable=False)
    department: Mapped[str | None] = mapped_column(String(80), nullable=True)
    assigned_staff_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    image_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Low")
    risk_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tracking_code: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True, default=generate_tracking_code)
    building: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    equipment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Image and fusion details: which model, scores, hazard, routing reason. Advisory only.
    ai_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class IssueStatusHistory(Base):
    __tablename__ = "issue_status_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(80), nullable=False, default="system")


class ResponseTarget(Base):
    """Configurable response targets per priority (feature 2). Edited by administrators."""
    __tablename__ = "response_targets"
    priority: Mapped[str] = mapped_column(String(20), primary_key=True)
    start_within_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolve_within_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    auto_escalate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_by: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Escalation(Base):
    """A report that missed its response target and was raised to administrators."""
    __tablename__ = "escalations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    # "start": not started in time; "resolve": not resolved in time.
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    target_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    escalated_to: Mapped[str] = mapped_column(String(40), nullable=False, default="administrators")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
