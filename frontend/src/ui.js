// Shared display helpers. Pure functions only (no components), so they are easy to test.

export const CATEGORY_NAMES = {
  Facility: "Facility", Electrical: "Electrical", Plumbing: "Plumbing", HVAC: "HVAC",
  IT: "IT Infrastructure", Cleaning: "Cleaning", Safety: "Safety", Other: "Other",
};
export const CATEGORIES = Object.keys(CATEGORY_NAMES);

export const DEPARTMENT_BY_CATEGORY = {
  Electrical: "Electrical Maintenance", Plumbing: "Plumbing Maintenance", Cleaning: "Cleaning Services",
  Safety: "Campus Safety", Facility: "Facilities Maintenance", HVAC: "HVAC Maintenance",
  IT: "IT Infrastructure", Other: "Campus Administration",
};
export const DEPARTMENTS = [
  "Electrical Maintenance", "Plumbing Maintenance", "HVAC Maintenance", "IT Infrastructure",
  "Facilities Maintenance", "Cleaning Services", "Campus Safety", "Campus Administration",
];

export const categoryName = c => CATEGORY_NAMES[c] || c || "Uncategorised";
export const isOpen = i => !["resolved", "closed"].includes((i?.status || "").toLowerCase());
const PRIORITY_RANK = {high: 0, medium: 1, low: 2};
export const priorityRank = p => PRIORITY_RANK[(p || "").toLowerCase()] ?? 3;
export const toneOf = value => (value || "").toLowerCase().replaceAll(" ", "-");

/** "Library" from building, else the first part of a free-text location. */
export function buildingOf(issue) {
  if (issue?.building?.trim()) return issue.building.trim();
  const first = (issue?.location || "").split(/[,·]/)[0].trim();
  return first || "Unspecified";
}

/** Human duration: "45 min", "3 h 10 min", "2 days 4 h". */
export function formatDuration(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "";
  const minutes = Math.floor(ms / 60000);
  if (minutes < 1) return "under 1 min";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return minutes % 60 ? `${hours} h ${minutes % 60} min` : `${hours} h`;
  const days = Math.floor(hours / 24);
  return hours % 24 ? `${days} ${days === 1 ? "day" : "days"} ${hours % 24} h` : `${days} ${days === 1 ? "day" : "days"}`;
}

export function timeAgo(date, now = Date.now()) {
  const t = new Date(date).getTime();
  if (!Number.isFinite(t)) return "";
  const text = formatDuration(now - t);
  return text === "under 1 min" ? "just now" : `${text} ago`;
}

export const formatDate = d => {
  const t = new Date(d);
  return Number.isFinite(t.getTime()) ? t.toLocaleDateString(undefined, {year: "numeric", month: "short", day: "numeric"}) : "";
};
export const formatDateTime = d => {
  const t = new Date(d);
  return Number.isFinite(t.getTime()) ? t.toLocaleString(undefined, {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"}) : "";
};

/** Response and resolution times from a status history (real timestamps only). */
export function responseTimes(createdAt, history = []) {
  const start = new Date(createdAt).getTime();
  const firstAt = s => history.find(h => h.new_status === s)?.changed_at;
  const started = firstAt("In Progress");
  const resolved = firstAt("Resolved") || firstAt("Closed");
  return {
    response: started ? formatDuration(new Date(started).getTime() - start) : null,
    resolution: resolved ? formatDuration(new Date(resolved).getTime() - start) : null,
  };
}

/** Counts per ISO week (Monday start) for the last `weeks` weeks, oldest first. */
export function weeklyCounts(issues, weeks = 8, now = new Date()) {
  const monday = new Date(now);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  const buckets = Array.from({length: weeks}, (_, k) => {
    const start = new Date(monday);
    start.setDate(start.getDate() - 7 * (weeks - 1 - k));
    return {start, count: 0};
  });
  const first = buckets[0].start.getTime();
  issues.forEach(i => {
    const t = new Date(i.created_at).getTime();
    if (!Number.isFinite(t) || t < first) return;
    const index = Math.min(weeks - 1, Math.floor((t - first) / (7 * 86400000)));
    buckets[index].count += 1;
  });
  return buckets.map(b => ({label: b.start.toLocaleDateString(undefined, {month: "short", day: "numeric"}), count: b.count}));
}

/** Display status: "Assigned" is a Submitted report that already has a staff member. */
export const displayStatus = i => (i?.status === "Submitted" && i?.assigned_staff_id ? "Assigned" : i?.status || "Unknown");

/** Safety severity comes from the triage risk level stored with each report. */
export const severityOf = level => ({High: "High", Moderate: "Medium", Low: "Low"}[level] || "Low");

export const MATCH_STRENGTH = {
  strong: {label: "Strong match", level: 3},
  moderate: {label: "Moderate match", level: 2},
  uncertain: {label: "Uncertain", level: 1},
};

// Response targets (feature 2). Mirrors backend/app/escalation.py; the server's values win when loaded.
export const DEFAULT_TARGETS = {
  High: {start_within_minutes: 240, resolve_within_minutes: 1440, auto_escalate: true},
  Medium: {start_within_minutes: 1440, resolve_within_minutes: 4320, auto_escalate: false},
  Low: {start_within_minutes: 4320, resolve_within_minutes: 10080, auto_escalate: false},
};
export const targetMap = list => {
  const map = {...DEFAULT_TARGETS};
  (list || []).forEach(t => { map[t.priority] = t; });
  return map;
};

/** Missed targets for an open report: [{kind: "start"|"resolve", dueAt, overdueMs}]. */
export function overdueOf(issue, targets, now = Date.now()) {
  if (!isOpen(issue)) return [];
  const t = targets?.[issue.priority] || DEFAULT_TARGETS[issue.priority];
  const created = new Date(issue.created_at).getTime();
  if (!t || !Number.isFinite(created)) return [];
  const out = [];
  const startDue = created + t.start_within_minutes * 60000;
  if (issue.status === "Submitted" && now > startDue) out.push({kind: "start", dueAt: startDue, overdueMs: now - startDue});
  const resolveDue = created + t.resolve_within_minutes * 60000;
  if (now > resolveDue) out.push({kind: "resolve", dueAt: resolveDue, overdueMs: now - resolveDue});
  return out;
}

/** Short due/overdue text for task lists, e.g. "Start overdue by 2 h" or "Resolve due in 5 h". */
export function dueText(issue, targets, now = Date.now()) {
  if (!isOpen(issue)) return "";
  const late = overdueOf(issue, targets, now);
  if (late.length) {
    const worst = late[late.length - 1];
    return `${worst.kind === "start" ? "Start" : "Resolve"} overdue by ${formatDuration(worst.overdueMs)}`;
  }
  const t = targets?.[issue.priority] || DEFAULT_TARGETS[issue.priority];
  if (!t) return "";
  const created = new Date(issue.created_at).getTime();
  const kind = issue.status === "Submitted" ? "start" : "resolve";
  const due = created + (kind === "start" ? t.start_within_minutes : t.resolve_within_minutes) * 60000;
  return `${kind === "start" ? "Start" : "Resolve"} due in ${formatDuration(due - now)}`;
}

export const minutesLabel = m => (m % 1440 === 0 ? `${m / 1440} ${m === 1440 ? "day" : "days"}` : m % 60 === 0 ? `${m / 60} h` : `${m} min`);
