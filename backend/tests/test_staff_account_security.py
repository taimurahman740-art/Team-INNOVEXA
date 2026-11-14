import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import StaffUser
from app.auth import hash_password, create_access_token


@pytest.fixture()
def client_and_users(monkeypatch):
    monkeypatch.setenv("STAFF_TOKEN_SECRET", "test-secret-that-is-at-least-32-characters-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    admin = StaffUser(email="admin@example.com", full_name="Admin", password_hash=hash_password("AdminPassword123"), department="Campus Administration", role="admin", is_active=True)
    staff = StaffUser(email="staff@example.com", full_name="Staff", password_hash=hash_password("StaffPassword123"), department="Facilities Maintenance", role="staff", is_active=True)
    db.add_all([admin, staff])
    db.commit()
    db.refresh(admin)
    db.refresh(staff)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client, admin, staff, db
    test_client.close()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_password_change_invalidates_existing_session(client_and_users):
    client, admin, staff, db = client_and_users
    old_token = create_access_token(staff)
    response = client.patch("/issues/staff/me/password", headers=auth(old_token), json={
        "current_password": "StaffPassword123",
        "new_password": "NewStaffPassword456",
    })
    assert response.status_code == 200
    assert client.get("/issues/staff/me", headers=auth(old_token)).status_code == 401
    login = client.post("/issues/staff/login", json={"email": staff.email, "password": "NewStaffPassword456"})
    assert login.status_code == 200


def test_admin_reset_invalidates_old_session(client_and_users):
    client, admin, staff, db = client_and_users
    admin_token = create_access_token(admin)
    staff_token = create_access_token(staff)
    response = client.post(f"/issues/staff/users/{staff.id}/reset-password", headers=auth(admin_token), json={
        "new_password": "ResetStaffPassword789",
    })
    assert response.status_code == 200
    assert client.get("/issues/staff/me", headers=auth(staff_token)).status_code == 401
    assert client.post("/issues/staff/login", json={"email": staff.email, "password": "ResetStaffPassword789"}).status_code == 200


def test_deactivation_blocks_existing_session(client_and_users):
    client, admin, staff, db = client_and_users
    admin_token = create_access_token(admin)
    staff_token = create_access_token(staff)
    response = client.patch(f"/issues/staff/users/{staff.id}/active", headers=auth(admin_token), json={"is_active": False})
    assert response.status_code == 200
    assert client.get("/issues/staff/me", headers=auth(staff_token)).status_code == 401


def test_last_admin_cannot_be_deactivated(client_and_users):
    client, admin, staff, db = client_and_users
    response = client.patch(f"/issues/staff/users/{admin.id}/active", headers=auth(create_access_token(admin)), json={"is_active": False})
    assert response.status_code == 422


def test_staff_cannot_manage_accounts(client_and_users):
    client, admin, staff, db = client_and_users
    response = client.patch(f"/issues/staff/users/{staff.id}/active", headers=auth(create_access_token(staff)), json={"is_active": False})
    assert response.status_code == 403
