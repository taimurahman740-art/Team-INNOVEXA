# INNOVEXA deployment setup

## Current application workflow

- Students can submit reports without an account.
- A small supervised Multinomial Naive Bayes text classifier suggests an issue category.
- Safety keywords provide a preliminary Low/Medium/High priority suggestion.
- The category maps to a responsible department.
- Optional PNG, JPEG, or WEBP evidence photos (maximum 2 MB) are stored in PostgreSQL with the report.
- The public dashboard exposes limited metadata only; full descriptions, exact locations, photos and risk details are available only through the staff-key-protected endpoint.
- Staff status changes require the API key configured below.

## Required one-time Render configuration

The repository code cannot create a private secret inside your Render account. Set it once:

1. Open the Render Dashboard and select the **innovexa-api** web service.
2. Open **Environment**.
3. Add an environment variable:
   - Key: `STAFF_API_KEY`
   - Value: create a long random password (at least 32 characters). Do not reuse your normal password.
4. Add the image-model token as a second environment variable:
   - Key: `HF_TOKEN`
   - Value: a Hugging Face fine-grained token with **Make calls to Inference Providers** permission. Create it in Hugging Face token settings. Never put this token in frontend code or commit it to GitHub.
5. Optionally set `HF_IMAGE_MODEL` to override the default `openai/clip-vit-large-patch14` model.
6. Save changes and let the backend redeploy.
7. Give the staff key only to authorized staff. Enter it in the Staff Task Centre to enable status updates.

If `STAFF_API_KEY` is missing, the public report list and student submissions continue to work, but staff status updates are intentionally disabled.

## Important prototype limitations

- The text classifier is trained on a small hand-labelled starter dataset and public-board paraphrases. The image classifier is a general pretrained zero-shot model, not trained or validated on campus photos. Both are prototype suggestions; collect consented, labelled campus examples and evaluate them before operational use.
- Priority is a transparent keyword-based heuristic, not a medical or safety assessment. Staff must independently assess urgent reports.
- The staff key is a shared prototype credential, not individual user accounts, role-based access control, or an audit trail. Use institutional SSO or individual accounts before real campus deployment.
- Images are stored in PostgreSQL. The optional AI category suggestion sends the uploaded image bytes to the configured Hugging Face Inference Provider. Review provider terms and privacy requirements before using real student images; keep uploads small and arrange backups and retention rules.
- Public visitors can see limited report metadata (title, category, priority, status, department and date). Full descriptions, exact locations, photos and risk details are protected by the staff key. Do not submit personal, confidential, or sensitive information.
- Notifications, individual student tracking, and verified identity are not implemented.
- For immediate danger, contact campus security or emergency services directly.

## Verification checklist

1. Submit a report with an attached photo.
2. Confirm the category, priority, and department suggestions.
3. Refresh the page and confirm the report and image remain visible.
4. Open Staff Tasks, enter the configured staff key, and move a report to In Progress.
5. Confirm detailed report information and photos are visible only after staff authorization.\n6. Mark it Resolved and confirm the new status appears after refresh.
