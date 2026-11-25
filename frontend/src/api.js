const PRODUCTION_API = "https://innovexa-api-lfjx.onrender.com";
// In `npm run dev` the default is the local backend, so a missing .env never writes to production.
const configuredBase = (import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://localhost:8000" : PRODUCTION_API)).replace(/\/$/, "");
const BASE = /^https?:\/\//i.test(configuredBase) ? configuredBase : `https://${configuredBase}`;
const TIMEOUT_MS = 60_000; // free hosting can take a while to wake up

// FastAPI sends `detail` as a string for HTTPException but as a list of {msg, loc} for validation errors.
function errorMessage(text, status) {
  try {
    const detail = JSON.parse(text).detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail) && detail.length) return detail.map(d => d?.msg || "Invalid input").join("; ");
  } catch {}
  return text || `Request failed (${status})`;
}

async function request(path, options = {}) {
  const {token, ...rest} = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        ...(rest.body ? {"Content-Type": "application/json"} : {}), // no preflight-forcing header on plain GETs
        ...(token ? {Authorization: `Bearer ${token}`} : {}),
        ...(rest.headers || {}),
      },
    });
  } catch (err) {
    if (err?.name === "AbortError") throw new Error("The server took too long to respond. Please try again.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) throw new Error(errorMessage(await response.text(), response.status));
  return response.json();
}
export const getIssues = () => request("/issues");
export const postIssue = (issue) => request("/issues", {method:"POST",body:JSON.stringify(issue)});
export const classifyImage = (image_data) => request("/issues/image-classification", {method:"POST",body:JSON.stringify({image_data})});
export const getIssueTracking = (code) => request(`/issues/track/${encodeURIComponent(code)}`);
export const getStaffSetupStatus = () => request("/issues/staff/setup-status");
export const bootstrapStaffAdmin = (account) => request("/issues/staff/bootstrap",{method:"POST",body:JSON.stringify(account)});
export const loginStaff = (email,password) => request("/issues/staff/login",{method:"POST",body:JSON.stringify({email,password})});
export const getStaffIssues = (token) => request("/issues/staff",{token});
export const getStaffUsers = (token) => request("/issues/staff/users",{token});
export const createStaffUser = (account,token) => request("/issues/staff/users",{method:"POST",token,body:JSON.stringify(account)});
// resolution_note is optional; it is only sent when given, so plain status changes keep the old request body.
export const patchStatus = (id,status,token,resolution_note) => request(`/issues/${id}/status`,{method:"PATCH",token,body:JSON.stringify(resolution_note===undefined?{status}:{status,resolution_note})});
export const assignIssue = (id,staff_user_id,token) => request(`/issues/${id}/assignment`,{method:"PATCH",token,body:JSON.stringify({staff_user_id})});
export const getIssueHistory = (id,token) => request(`/issues/${id}/history`,{token});
export const changeStaffPassword = (current_password,new_password,token) => request("/issues/staff/me/password",{method:"PATCH",token,body:JSON.stringify({current_password,new_password})});
export const setStaffActive = (id,is_active,token) => request(`/issues/staff/users/${id}/active`,{method:"PATCH",token,body:JSON.stringify({is_active})});
export const resetStaffPassword = (id,new_password,token) => request(`/issues/staff/users/${id}/reset-password`,{method:"POST",token,body:JSON.stringify({new_password})});
export const getResponseTimes = (token) => request("/issues/analytics/response-times",{token});
