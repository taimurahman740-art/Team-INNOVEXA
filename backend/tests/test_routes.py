"""API regression tests using an isolated in-memory SQLite database."""
import os
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.routes import router

class IssueApiTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
        self.Session=sessionmaker(bind=self.engine,autoflush=False,autocommit=False)
        Base.metadata.create_all(bind=self.engine)
        def override_get_db():
            db=self.Session()
            try: yield db
            finally: db.close()
        app=FastAPI();app.include_router(router);app.dependency_overrides[get_db]=override_get_db
        self.client=TestClient(app)
        self.env=patch.dict(os.environ,{"STAFF_TOKEN_SECRET":"test-secret-value-with-at-least-32-characters","STAFF_BOOTSTRAP_KEY":"test-bootstrap-key"})
        self.env.start()
    def tearDown(self):
        self.env.stop();self.client.close();Base.metadata.drop_all(bind=self.engine);self.engine.dispose()
    def payload(self,**overrides):
        data={"title":"Broken classroom light","description":"The ceiling light does not turn on.","location":"Engineering Building Room 201","category":"Other"}
        data.update(overrides);return data
    def admin(self):
        r=self.client.post("/issues/staff/bootstrap",json={"bootstrap_key":"test-bootstrap-key","email":"admin@campus.test","full_name":"Campus Admin","password":"secure-admin-password","department":"Campus Administration"})
        self.assertEqual(r.status_code,201,r.text);return r.json()
    def add_staff(self,token,email="tech@campus.test",department="Electrical Maintenance"):
        r=self.client.post("/issues/staff/users",headers={"Authorization":"Bearer "+token},json={"email":email,"full_name":"Campus Technician","password":"secure-staff-password","department":department,"role":"staff"})
        self.assertEqual(r.status_code,201,r.text);return r.json()
    def test_public_submission_and_tracking_code(self):
        r=self.client.post("/issues",json=self.payload());self.assertEqual(r.status_code,201)
        issue=r.json();self.assertTrue(issue["tracking_code"].startswith("INX-"))
        tracked=self.client.get("/issues/track/"+issue["tracking_code"])
        self.assertEqual(tracked.status_code,200);self.assertEqual(tracked.json()["status"],"Submitted")
        self.assertNotIn("description",tracked.json());self.assertNotIn("location",tracked.json())
    def test_first_admin_bootstrap_is_one_time_and_password_login_works(self):
        created=self.admin();self.assertEqual(created["user"]["role"],"admin")
        duplicate=self.client.post("/issues/staff/bootstrap",json={"bootstrap_key":"test-bootstrap-key","email":"other@campus.test","full_name":"Other Admin","password":"another-secure-password"})
        self.assertEqual(duplicate.status_code,409)
        login=self.client.post("/issues/staff/login",json={"email":"ADMIN@campus.test","password":"secure-admin-password"})
        self.assertEqual(login.status_code,200);self.assertNotIn("password_hash",login.json()["user"])
    def test_bad_bootstrap_key_and_password_are_rejected(self):
        bad=self.client.post("/issues/staff/bootstrap",json={"bootstrap_key":"bad","email":"admin@campus.test","full_name":"Campus Admin","password":"secure-admin-password"})
        self.assertEqual(bad.status_code,401);self.admin()
        bad_login=self.client.post("/issues/staff/login",json={"email":"admin@campus.test","password":"wrong-password"})
        self.assertEqual(bad_login.status_code,401)
    def test_department_scoped_access_and_admin_assignment(self):
        admin_token=self.admin()["access_token"];staff=self.add_staff(admin_token)
        issue=self.client.post("/issues",json=self.payload(category="Electrical")).json()
        assigned=self.client.patch(f"/issues/{issue['id']}/assignment",headers={"Authorization":"Bearer "+admin_token},json={"staff_user_id":staff["id"]})
        self.assertEqual(assigned.status_code,200);self.assertEqual(assigned.json()["assigned_staff_id"],staff["id"])
        login=self.client.post("/issues/staff/login",json={"email":"tech@campus.test","password":"secure-staff-password"}).json()
        token=login["access_token"];tasks=self.client.get("/issues/staff",headers={"Authorization":"Bearer "+token})
        self.assertEqual([x["id"] for x in tasks.json()],[issue["id"]])
        changed=self.client.patch(f"/issues/{issue['id']}/status",headers={"Authorization":"Bearer "+token},json={"status":"In Progress"})
        self.assertEqual(changed.status_code,200);self.assertEqual(changed.json()["status"],"In Progress")
        history=self.client.get(f"/issues/{issue['id']}/history",headers={"Authorization":"Bearer "+token})
        self.assertEqual(history.json()[-1]["changed_by"],"tech@campus.test")
    def test_staff_cannot_work_on_another_staff_assignment_or_department(self):
        admin_token=self.admin()["access_token"];first=self.add_staff(admin_token,"one@campus.test");second=self.add_staff(admin_token,"two@campus.test")
        issue=self.client.post("/issues",json=self.payload(category="Electrical")).json()
        unassigned=self.client.post("/issues",json=self.payload(title="Unassigned electrical socket",category="Electrical")).json()
        self.client.patch(f"/issues/{issue['id']}/assignment",headers={"Authorization":"Bearer "+admin_token},json={"staff_user_id":second["id"]})
        token=self.client.post("/issues/staff/login",json={"email":"one@campus.test","password":"secure-staff-password"}).json()["access_token"]
        denied=self.client.patch(f"/issues/{issue['id']}/status",headers={"Authorization":"Bearer "+token},json={"status":"In Progress"})
        self.assertEqual(denied.status_code,403)
        hidden=self.client.get("/issues/staff",headers={"Authorization":"Bearer "+token})
        self.assertEqual([item["id"] for item in hidden.json()],[unassigned["id"]])
        history_denied=self.client.get(f"/issues/{issue['id']}/history",headers={"Authorization":"Bearer "+token})
        self.assertEqual(history_denied.status_code,403)
        plumber=self.add_staff(admin_token,"plumber@campus.test","Plumbing Maintenance")
        wrong_department=self.client.patch(f"/issues/{issue['id']}/assignment",headers={"Authorization":"Bearer "+admin_token},json={"staff_user_id":plumber["id"]})
        self.assertEqual(wrong_department.status_code,422)
        plumber_token=self.client.post("/issues/staff/login",json={"email":"plumber@campus.test","password":"secure-staff-password"}).json()["access_token"]
        cross=self.client.patch(f"/issues/{issue['id']}/status",headers={"Authorization":"Bearer "+plumber_token},json={"status":"Resolved"})
        self.assertEqual(cross.status_code,403)
        plumber_tasks=self.client.get("/issues/staff",headers={"Authorization":"Bearer "+plumber_token})
        self.assertEqual(plumber_tasks.json(),[])
    def test_only_admin_can_manage_staff_accounts(self):
        admin_token=self.admin()["access_token"];self.add_staff(admin_token)
        token=self.client.post("/issues/staff/login",json={"email":"tech@campus.test","password":"secure-staff-password"}).json()["access_token"]
        denied=self.client.get("/issues/staff/users",headers={"Authorization":"Bearer "+token})
        self.assertEqual(denied.status_code,403)
        self.assertEqual(self.client.get("/issues/staff").status_code,401)
    def test_public_overview_hides_private_fields(self):
        self.client.post("/issues",json=self.payload());item=self.client.get("/issues").json()[0]
        self.assertNotIn("description",item);self.assertNotIn("location",item);self.assertNotIn("image_data",item)
    def test_image_classification_validation_and_provider_error(self):
        invalid=self.client.post("/issues",json=self.payload(image_data="not-an-image"));self.assertEqual(invalid.status_code,422)
        with patch.dict(os.environ,{"HF_TOKEN":""}):
            response=self.client.post("/issues/image-classification",json={"image_data":"data:image/png;base64,iVBORw0KGgo="})
        self.assertEqual(response.status_code,503)
    def test_high_risk_report_cannot_be_downgraded(self):
        r=self.client.post("/issues",json=self.payload(title="Water near electrical outlet",description="Water is dripping beside a live power outlet.",priority="Low"))
        self.assertEqual(r.status_code,201);self.assertEqual(r.json()["risk_level"],"High");self.assertEqual(r.json()["priority"],"High")
    def test_routine_report_can_keep_submitted_priority(self):
        r=self.client.post("/issues",json=self.payload(title="Broken classroom chair",description="One chair leg is damaged and needs repair.",priority="Low"))
        self.assertEqual(r.status_code,201);self.assertEqual(r.json()["priority"],"Low")

if __name__=="__main__": unittest.main()
