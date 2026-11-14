const configuredBase = (import.meta.env.VITE_API_BASE_URL || "https://innovexa-api-lfjx.onrender.com").replace(/\/$/, "");
const BASE = /^https?:\/\//i.test(configuredBase) ? configuredBase : `https://${configuredBase}`;
async function request(path, options = {}) {
  const {token, ...rest} = options;
  const response = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: {"Content-Type":"application/json", ...(token ? {Authorization:`Bearer ${token}`} : {}), ...(rest.headers || {})},
  });
  if (!response.ok) {
    let message = await response.text();
    try { message = JSON.parse(message).detail || message; } catch {}
    throw new Error(message || `Request failed (${response.status})`);
  }
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
export const patchStatus = (id,status,token) => request(`/issues/${id}/status`,{method:"PATCH",token,body:JSON.stringify({status})});
export const assignIssue = (id,staff_user_id,token) => request(`/issues/${id}/assignment`,{method:"PATCH",token,body:JSON.stringify({staff_user_id})});
export const getIssueHistory = (id,token) => request(`/issues/${id}/history`,{token});

export const changeStaffPassword = (current_password,new_password,token) => request("/issues/staff/me/password",{method:"PATCH",token,body:JSON.stringify({current_password,new_password})});
export const setStaffActive = (id,is_active,token) => request(`/issues/staff/users/${id}/active`,{method:"PATCH",token,body:JSON.stringify({is_active})});
export const resetStaffPassword = (id,new_password,token) => request(`/issues/staff/users/${id}/reset-password`,{method:"POST",token,body:JSON.stringify({new_password})});
