"""Administrator and self-service staff account management."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import get_current_staff, hash_password, require_admin, verify_password
from .database import get_db
from .models import StaffUser

router = APIRouter(prefix="/issues/staff", tags=["staff accounts"])


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=12, max_length=200)


class AccountActiveUpdate(BaseModel):
    is_active: bool


@router.patch("/me/password")
def change_own_password(payload: PasswordChange, user: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=422, detail="Choose a different password.")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


@router.patch("/users/{user_id}/active")
def set_staff_active(user_id: int, payload: AccountActiveUpdate, admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    member = db.get(StaffUser, user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Staff account not found.")
    if member.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=422, detail="You cannot deactivate your own administrator account.")
    if member.role == "admin" and member.is_active and not payload.is_active:
        active_admins = db.scalar(select(func.count(StaffUser.id)).where(StaffUser.role == "admin", StaffUser.is_active.is_(True))) or 0
        if active_admins <= 1:
            raise HTTPException(status_code=422, detail="The last active administrator cannot be deactivated.")
    member.is_active = payload.is_active
    db.commit()
    return {"id": member.id, "is_active": member.is_active}


@router.post("/users/{user_id}/reset-password")
def reset_staff_password(user_id: int, payload: PasswordReset, admin: StaffUser = Depends(require_admin), db: Session = Depends(get_db)):
    member = db.get(StaffUser, user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Staff account not found.")
    member.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successfully."}
