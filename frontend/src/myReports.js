// Reports submitted from this device. There are no student accounts, so the
// tracking codes are kept in this browser and the live status is read by code.
const KEY = "innovexa.myReports.v1";

export function loadMyReports() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(value) ? value.filter(r => r && typeof r.code === "string") : [];
  } catch {
    return [];
  }
}

export function saveMyReports(list) {
  try { localStorage.setItem(KEY, JSON.stringify(list.slice(0, 50))); } catch { /* storage unavailable */ }
}

export function rememberReport(issue) {
  if (!issue?.tracking_code) return loadMyReports();
  const list = [{code: issue.tracking_code, title: issue.title, submitted_at: issue.created_at, last_status: issue.status, seen_status: issue.status},
    ...loadMyReports().filter(r => r.code !== issue.tracking_code)];
  saveMyReports(list);
  return list;
}

/** Merge fresh tracking results; a status that differs from the last one seen becomes a notification. */
export function mergeTracking(list, results) {
  return list.map(r => {
    const fresh = results[r.code];
    return fresh ? {...r, title: fresh.title, last_status: fresh.status, history: fresh.history, category: fresh.category, department: fresh.department, priority: fresh.priority} : r;
  });
}

export const unreadUpdates = list => list.filter(r => r.last_status && r.seen_status && r.last_status !== r.seen_status);
export const markAllSeen = list => list.map(r => ({...r, seen_status: r.last_status}));
