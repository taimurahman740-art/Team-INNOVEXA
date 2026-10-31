# INNOVEXA deployment setup

## Current application workflow

- Students can submit reports without an account.
- A small supervised Multinomial Naive Bayes text classifier suggests an issue category.
- Safety keywords provide a preliminary Low/Medium/High priority suggestion.
- The category maps to a responsible department.
- Optional PNG, JPEG, or WEBP evidence photos (maximum 2 MB) are stored in PostgreSQL with the report.
- Reports remain visible in the public dashboard.
- Staff status changes require the API key configured below.

## Required one-time Render configuration

The repository code cannot create a private secret inside your Render account. Set it once:

1. Open the Render Dashboard and select the **innovexa-api** web service.
2. Open **Environment**.
3. Add an environment variable:
   - Key: `STAFF_API_KEY`
   - Value: create a long random password (at least 32 characters). Do not reuse your normal password.
4. Save changes and let the backend redeploy.
5. Give this key only to authorized staff. Enter it in the Staff Task Centre to enable status updates.

If `STAFF_API_KEY` is missing, the public report list and student submissions continue to work, but staff status updates are intentionally disabled.

## Important prototype limitations

- The classifier is trained on a small hand-labelled starter dataset included in `app/services.py`. It is a demonstration model, not a validated campus safety model. Collect and label real campus examples, evaluate precision/recall, and retrain before operational use.
- Priority is a transparent keyword-based heuristic, not a medical or safety assessment. Staff must independently assess urgent reports.
- The staff key is a shared prototype credential, not individual user accounts, role-based access control, or an audit trail. Use institutional SSO or individual accounts before real campus deployment.
- Images are stored in PostgreSQL. Keep uploads small and arrange backups and retention rules before collecting real student data.
- Public report visibility means report text, locations, and attached photos can be seen by visitors. Do not upload personal, confidential, or sensitive information.
- Notifications, individual student tracking, and verified identity are not implemented.
- For immediate danger, contact campus security or emergency services directly.

## Verification checklist

1. Submit a report with an attached photo.
2. Confirm the category, priority, and department suggestions.
3. Refresh the page and confirm the report and image remain visible.
4. Open Staff Tasks, enter the configured staff key, and move a report to In Progress.
5. Mark it Resolved and confirm the new status appears after refresh.
