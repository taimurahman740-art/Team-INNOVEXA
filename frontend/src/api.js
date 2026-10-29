const configuredBase = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const BASE = /^https?:\/\//i.test(configuredBase) ? configuredBase : `https://${configuredBase}`;
async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {...options, headers: {"Content-Type": "application/json", ...(options.headers || {})}});
  if (!response.ok) throw new Error(await response.text() || `Request failed (${response.status})`);
  return response.json();
}
export const getIssues = () => request("/issues");
export const postIssue = (issue) => request("/issues", {method: "POST", body: JSON.stringify(issue)});
export const patchStatus = (id, status) => request(`/issues/${id}/status`, {method: "PATCH", body: JSON.stringify({status})});
