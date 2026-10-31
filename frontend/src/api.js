const configuredBase = (import.meta.env.VITE_API_BASE_URL || "https://innovexa-api-lfjx.onrender.com").replace(/\/$/, "");
const BASE = /^https?:\/\//i.test(configuredBase) ? configuredBase : `https://${configuredBase}`;
async function request(path, options = {}) {
  const {staffKey, ...rest} = options;
  const response = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: {"Content-Type": "application/json", ...(staffKey ? {"X-Staff-Key": staffKey} : {}), ...(rest.headers || {})},
  });
  if (!response.ok) {
    let message = await response.text();
    try { message = JSON.parse(message).detail || message; } catch {}
    throw new Error(message || `Request failed (${response.status})`);
  }
  return response.json();
}
export const getIssues = () => request("/issues");
export const postIssue = (issue) => request("/issues", {method: "POST", body: JSON.stringify(issue)});
export const patchStatus = (id, status, staffKey) => request(`/issues/${id}/status`, {method: "PATCH", staffKey, body: JSON.stringify({status})});
