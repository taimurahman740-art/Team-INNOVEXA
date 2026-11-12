# INNOVEXA deployment setup

## Staff account configuration

In Render, select the **innovexa-api** service and add these environment variables:

1. `STAFF_TOKEN_SECRET`: a randomly generated secret of at least 32 characters. Keep it private and stable; rotating it signs out all staff.
2. `STAFF_BOOTSTRAP_KEY`: a separate one-time key used only to create the first administrator. Give it only to that administrator, then remove it from Render after setup.
3. `HF_TOKEN`: optional Hugging Face fine-grained token with **Make calls to Inference Providers** permission.
4. `HF_IMAGE_MODEL`: optional model override.
5. `FRONTEND_ORIGINS`: recommended comma-separated list of trusted frontend origins instead of the wildcard default.

Save the environment and allow the backend to redeploy. Open **Staff tasks**, enter the one-time bootstrap key, and create the first administrator using a strong password. Remove `STAFF_BOOTSTRAP_KEY` from Render after successful setup. The administrator can create individual staff accounts, selecting a department and role.

The previous shared `STAFF_API_KEY` is no longer accepted. Existing reports and tracking codes are preserved by additive database migrations. Staff bearer sessions expire after eight hours.

## How access works

- Students continue to submit and track reports without an account.
- Administrators can see all departments, create staff accounts, and assign reports to active staff in the report's department.
- Staff can see reports routed to their own department. They can update unassigned tasks in that department or tasks assigned to them.
- Status history records the staff email responsible for each change.
- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes. Deploy over HTTPS and protect both secrets.

## Prototype limitations

Institutional SSO, MFA, password reset, invitation emails, and automated account lockout are not implemented. Administrators must distribute initial passwords securely. Classifier, image recognition and safety priority remain prototype aids and require human review. For immediate danger, contact campus security or emergency services directly.

## Verification checklist

1. Configure both staff secrets and redeploy the backend.
2. Create the first administrator, then remove `STAFF_BOOTSTRAP_KEY`.
3. Create an account for each department.
4. Submit an Electrical report and assign it to an Electrical Maintenance staff member.
5. Confirm a different department cannot view or update that report.
6. Confirm the assigned staff member can update status and the history records their email.
7. Confirm students can still submit and track reports.
