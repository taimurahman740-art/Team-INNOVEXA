import {useEffect, useMemo, useState} from "react";
import {AlertTriangle, ChevronRight, Copy, Clock3, Image as ImageIcon, KeyRound, LayoutDashboard, ListChecks, LockKeyhole, LogOut, MapPin, RefreshCw, Search, ShieldCheck, Siren, UserPlus, Users, X} from "lucide-react";
import AdminInsights from "./AdminInsights.jsx";
import {useStaffSession} from "./staffSession.js";
import {AiTag, CategoryTag, ConfirmDialog, EmptyState, Metric, PriorityBadge, SeverityBadge, SkeletonRows, StatusBadge} from "./components.jsx";
import {DEPARTMENTS, buildingOf, displayStatus, dueText, overdueOf, targetMap, formatDate, formatDateTime, formatDuration, isOpen, priorityRank, responseTimes, severityOf, timeAgo} from "./ui.js";

const STATUS_FILTERS = [["open", "All open"], ["Submitted", "Submitted"], ["Assigned", "Assigned"], ["In Progress", "In progress"], ["resolved", "Resolved"], ["all", "All statuses"]];
const SORTS = [["priority", "Priority, then oldest"], ["oldest", "Oldest first"], ["newest", "Newest first"]];
const emptyStaff = {full_name: "", email: "", password: "", department: "Facilities Maintenance", role: "staff"};

/** Plain-language account of how the stored priority was decided (no model percentages). */
function priorityExplanation(p) {
  const parts = [p.method === "random_forest"
    ? `The Random Forest model predicted ${p.predicted} priority.`
    : "The priority model was unavailable, so keyword rules were used."];
  if (p.safety_floor_applied) parts.push("The safety rules raised it to High.");
  if (p.reporter_choice) parts.push(`The reporter selected ${p.reporter_choice}.`);
  if (p.method === "random_forest" && p.rule_priority && p.rule_priority !== p.final) parts.push(`Keyword rules alone would have given ${p.rule_priority}.`);
  return parts.join(" ");
}

/** An unreviewed possible duplicate (feature 7). */
const possibleDuplicate = issue => (issue.ai_analysis?.duplicates?.matches?.length || 0) > 0 && !issue.ai_analysis.duplicates.review;

/** Similar open reports found when this report was submitted, with the staff review. */
function DuplicatePanel({issue, s}) {
  const d = issue.ai_analysis?.duplicates;
  if (!d) return <p className="muted">Duplicate check: not run (this report was submitted before duplicate detection was added).</p>;
  const review = d.review;
  return <>
    <h3 className="section-title">Duplicate check <AiTag/></h3>
    {d.method === "unavailable" && <p className="muted">The similarity check could not run for this report.</p>}
    {d.method !== "unavailable" && !d.matches?.length && <p className="muted">No similar open reports in the same department or building.</p>}
    {d.matches?.length > 0 && <ul className="duplicate-list">{d.matches.map(m => (
      <li key={m.issue_id}>
        <div><strong>#{m.issue_id} {m.title}</strong><span>{m.reasons.map((r, k) => (k ? r.charAt(0).toLowerCase() + r.slice(1) : r)).join(", ")}.</span></div>
        {!review && <button className="btn btn-secondary btn-sm" onClick={() => s.reviewDuplicateOf(issue.id, "duplicate", m.issue_id)}>Same problem as #{m.issue_id}</button>}
      </li>))}</ul>}
    {d.matches?.length > 0 && !review && <button className="btn btn-ghost btn-sm" onClick={() => s.reviewDuplicateOf(issue.id, "not_duplicate")}>Not a duplicate</button>}
    {review && <p className="review-note">{review.decision === "duplicate" ? `Confirmed duplicate of #${review.duplicate_of}` : "Reviewed: not a duplicate"}, by {review.reviewed_by} on {formatDateTime(review.reviewed_at)}. The report stays open until someone resolves it.</p>}
  </>;
}


function SignIn({s}) {
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [bootstrapKey, setBootstrapKey] = useState(""), [fullName, setFullName] = useState("");
  return <section className="panel auth-card">
    <div className="auth-icon"><ShieldCheck size={22} aria-hidden="true"/></div>
    <h2>{s.bootstrapMode ? "Create the first administrator" : "Staff sign in"}</h2>
    <p className="muted">{s.bootstrapMode ? "This one-time step creates the administrator account. It needs the setup key from the server configuration." : "Use your individual staff account. Each account belongs to one department."}</p>
    {s.error && <div className="banner banner-error" role="alert">{s.error}</div>}
    {s.success && <div className="banner banner-ok" role="status">{s.success}</div>}
    <form className="form-stack" onSubmit={e => { e.preventDefault(); s.signIn({email, password, bootstrapKey, fullName}).then(ok => { if (ok) { setPassword(""); setBootstrapKey(""); } }); }}>
      {s.bootstrapMode && <><label className="field">Administrator name<input required value={fullName} onChange={e => setFullName(e.target.value)}/></label><label className="field">One-time setup key<input required type="password" value={bootstrapKey} onChange={e => setBootstrapKey(e.target.value)} placeholder="STAFF_BOOTSTRAP_KEY"/></label></>}
      <label className="field">Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="username"/></label>
      <label className="field">Password<input required type="password" minLength="12" value={password} onChange={e => setPassword(e.target.value)} autoComplete={s.bootstrapMode ? "new-password" : "current-password"}/></label>
      <button className="btn btn-primary btn-block" disabled={s.busy}><LockKeyhole size={16}/>{s.busy ? "Please wait…" : s.bootstrapMode ? "Create administrator" : "Sign in"}</button>
    </form>
    {!s.bootstrapMode && <p className="field-hint">Shared staff keys are no longer accepted. Ask your administrator for an account.</p>}
    {s.setupAvailable && !s.bootstrapMode && <button className="btn btn-ghost" onClick={() => s.setBootstrapMode(true)}>Initial administrator setup</button>}
  </section>;
}

function TaskDrawer({issue, s, onClose, onResolve}) {
  const user = s.user;
  useEffect(() => { s.loadHistory(issue.id); }, [issue.id]);
  useEffect(() => { const k = e => { if (e.key === "Escape") onClose(); }; window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k); }, [onClose]);
  const rows = s.history[issue.id];
  const times = rows ? responseTimes(issue.created_at, rows) : null;
  const ai = issue.ai_analysis;
  return <div className="drawer-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
    <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <header className="drawer-head">
        <div><span className="code-label">Report #{issue.id}</span><h2 id="drawer-title">{issue.title}</h2></div>
        <button className="icon-btn" onClick={onClose} aria-label="Close details"><X size={20}/></button>
      </header>
      <div className="drawer-body">
        <div className="detail-badges"><StatusBadge status={displayStatus(issue)}/><PriorityBadge priority={issue.priority}/><SeverityBadge severity={severityOf(issue.risk_level)}/></div>
        {issue.image_data ? <img className="drawer-photo" src={issue.image_data} alt="Report attachment"/> : <div className="no-photo"><ImageIcon size={18} aria-hidden="true"/>No photo attached</div>}
        <dl className="detail-grid">
          <div><dt>Location</dt><dd>{issue.location}</dd></div>
          <div><dt>Building</dt><dd>{buildingOf(issue)}</dd></div>
          {issue.equipment && <div><dt>Equipment</dt><dd>{issue.equipment}</dd></div>}
          <div><dt>Category</dt><dd><CategoryTag category={issue.category}/></dd></div>
          <div><dt>Department</dt><dd>{issue.department}</dd></div>
          <div><dt>Submitted</dt><dd>{formatDateTime(issue.created_at)}</dd></div>
          <div><dt>Assigned</dt><dd>{issue.assigned_staff_id ? (issue.assigned_staff_id === user.id ? "You" : s.staffUsers.find(m => m.id === issue.assigned_staff_id)?.full_name || `Staff #${issue.assigned_staff_id}`) : "Unassigned"}</dd></div>
        </dl>
        <h3 className="section-title">Description</h3>
        <p className="prose">{issue.description}</p>
        {issue.resolution_note && <><h3 className="section-title">Resolution note</h3><p className="prose">{issue.resolution_note}</p></>}
        <h3 className="section-title">Safety triage</h3>
        <p className="muted">Severity score {issue.risk_score ?? 0} of 10, from safety keywords{ai?.image?.hazard ? " and the photo" : ""}.</p>
        {issue.risk_reasons?.length > 0 ? <ul className="reason-list">{issue.risk_reasons.map(r => <li key={r}>{r}</li>)}</ul> : <p className="muted">No safety keywords found.</p>}
        {ai && <>
          <h3 className="section-title">AI routing <AiTag/></h3>
          <p className="prose">{ai.routing_reason}{ai.image_only ? " The reporter sent only a photo; the text was suggested from it." : ""}</p>
          {ai.image?.hazard && <div className="hazard hazard-found"><AlertTriangle size={16} aria-hidden="true"/><div><strong>Photo may show {ai.image.hazard.label.toLowerCase()}</strong><span>Confirm on site before closing the report.</span></div></div>}
        </>}
        {ai?.priority && <>
          <h3 className="section-title">Priority prediction <AiTag/></h3>
          <p className="prose">{priorityExplanation(ai.priority)}</p>
          {ai.priority.factors?.length > 0 && <ul className="reason-list">{ai.priority.factors.map(f => <li key={f}>{f}</li>)}</ul>}
        </>}
        <DuplicatePanel issue={issue} s={s}/>
        <h3 className="section-title">Status history</h3>
        {!rows ? <div className="skeleton-line"/> : <>
          {times && (times.response || times.resolution) && <p className="response-times">{times.response && <span>Work started after <b>{times.response}</b></span>}{times.resolution && <span>Resolved after <b>{times.resolution}</b></span>}</p>}
          <ol className="timeline compact">{rows.map(h => <li key={h.id}><strong>{h.old_status || "Created"} to {h.new_status}</strong><span>{formatDateTime(h.changed_at)}, {h.changed_by}</span></li>)}</ol>
        </>}
      </div>
      {isOpen(issue) && <footer className="drawer-foot">
        {issue.status === "Submitted" && <button className="btn btn-secondary" onClick={() => s.changeStatus(issue.id, "In Progress")}>Start work</button>}
        <button className="btn btn-primary" onClick={() => onResolve(issue)}>Mark resolved</button>
      </footer>}
    </aside>
  </div>;
}

function TaskList({s, scope, title, sub}) {
  const targets = targetMap(s.targets);
  const escalatedIds = new Set((s.escalations || []).filter(e => !e.acknowledged_at).map(e => e.issue_id));
  const user = s.user;
  const [query, setQuery] = useState(""), [status, setStatus] = useState("open"), [priority, setPriority] = useState("All"), [dept, setDept] = useState("All"), [sort, setSort] = useState("priority");
  const [detail, setDetail] = useState(null), [confirm, setConfirm] = useState(null), [note, setNote] = useState("");
  const tasks = useMemo(() => s.staffIssues
    .filter(i => scope !== "assigned" || i.assigned_staff_id === user.id)
    .filter(i => status === "all" || (status === "open" ? isOpen(i) : status === "resolved" ? !isOpen(i) : displayStatus(i) === status))
    .filter(i => priority === "All" || i.priority === priority)
    .filter(i => user.role !== "admin" || dept === "All" || i.department === dept)
    .filter(i => !query || [i.id, i.title, i.description, i.location, i.category, i.department].join(" ").toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => sort === "newest" ? new Date(b.created_at) - new Date(a.created_at)
      : sort === "oldest" ? new Date(a.created_at) - new Date(b.created_at)
      : priorityRank(a.priority) - priorityRank(b.priority) || new Date(a.created_at) - new Date(b.created_at)),
  [s.staffIssues, scope, status, priority, dept, query, sort, user]);
  const current = detail && s.staffIssues.find(i => i.id === detail);
  const filtered = query || status !== "open" || priority !== "All" || dept !== "All";

  return <section className="panel">
    <div className="panel-head"><div><h2>{title}</h2><p>{sub}</p></div><button className="btn btn-secondary btn-sm" onClick={s.refresh}><RefreshCw size={14}/>Refresh tasks</button></div>
    <div className="toolbar toolbar-wrap">
      <div className="search"><Search size={16} aria-hidden="true"/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search ID, title, location" aria-label="Search tasks"/></div>
      <label className="inline-select">Status<select value={status} onChange={e => setStatus(e.target.value)}>{STATUS_FILTERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      <label className="inline-select">Priority<select value={priority} onChange={e => setPriority(e.target.value)}><option>All</option><option>High</option><option>Medium</option><option>Low</option></select></label>
      {user.role === "admin" && <label className="inline-select">Department<select value={dept} onChange={e => setDept(e.target.value)}><option>All</option>{DEPARTMENTS.map(d => <option key={d}>{d}</option>)}</select></label>}
      <label className="inline-select">Sort<select value={sort} onChange={e => setSort(e.target.value)}>{SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      <span className="toolbar-count">{tasks.length} {tasks.length === 1 ? "task" : "tasks"}</span>
    </div>
    {!tasks.length ? <EmptyState icon={ListChecks} title={filtered ? "No tasks match these filters" : scope === "assigned" ? "Nothing is assigned to you" : "No open tasks"}
        action={filtered ? <button className="btn btn-secondary" onClick={() => { setQuery(""); setStatus("open"); setPriority("All"); setDept("All"); }}>Clear filters</button> : null}>
        {filtered ? "Try a different search or filter." : scope === "assigned" ? "When an administrator assigns you a report, it appears here." : "New reports for your department will appear here."}
      </EmptyState>
    : <div className="table-wrap"><table className="table task-table">
      <thead><tr><th scope="col">ID</th><th scope="col">Issue</th><th scope="col">Priority</th><th scope="col">Severity</th><th scope="col">Department</th><th scope="col">Submitted</th><th scope="col">Status</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
      <tbody>{tasks.map(i => <tr key={i.id} className={`edge-${(i.priority || "medium").toLowerCase()}`}>
        <td data-label="ID" className="cell-id">#{i.id}</td>
        <td data-label="Issue"><div className="cell-title"><h3>{i.title}</h3>{possibleDuplicate(i) && <span className="badge badge-duplicate"><Copy size={12} aria-hidden="true"/>Possible duplicate</span>}<span className="cell-sub"><MapPin size={13} aria-hidden="true"/>{i.location}</span><CategoryTag category={i.category}/></div></td>
        <td data-label="Priority"><PriorityBadge priority={i.priority}/></td>
        <td data-label="Severity"><SeverityBadge severity={severityOf(i.risk_level)}/></td>
        <td data-label="Department">{i.department}</td>
        <td data-label="Submitted"><span className="cell-date">{formatDate(i.created_at)}</span><span className="cell-sub"><Clock3 size={13} aria-hidden="true"/>{isOpen(i) ? `Open ${formatDuration(Date.now() - new Date(i.created_at).getTime())}` : timeAgo(i.created_at)}</span></td>
        <td data-label="Status"><div className="status-cell"><StatusBadge status={displayStatus(i)}/>{escalatedIds.has(i.id) && <span className="badge badge-escalated"><Siren size={12} aria-hidden="true"/>Escalated</span>}{isOpen(i) && <span className={`due-text ${overdueOf(i, targets).length ? "late" : ""}`}>{dueText(i, targets)}</span>}</div></td>
        <td data-label="Actions"><div className="row-actions">
          {user.role === "admin" && <label className="inline-select compact"><span className="visually-hidden">Assign to</span><select value={i.assigned_staff_id || ""} onChange={e => s.assign(i.id, e.target.value)}><option value="">Unassigned</option>{s.staffUsers.filter(m => m.is_active && m.role === "staff" && m.department === i.department).map(m => <option key={m.id} value={m.id}>{m.full_name}</option>)}</select></label>}
          {i.status === "Submitted" && <button className="btn btn-secondary btn-sm" onClick={() => s.changeStatus(i.id, "In Progress")}>Start work</button>}
          {isOpen(i) && <button className="btn btn-primary btn-sm" onClick={() => setConfirm(i)}>Mark resolved</button>}
          <button className="btn btn-ghost btn-sm" onClick={() => setDetail(i.id)} aria-label={`Details for report #${i.id}`}>Details<ChevronRight size={14}/></button>
        </div></td>
      </tr>)}</tbody>
    </table></div>}
    {current && <TaskDrawer issue={current} s={s} onClose={() => setDetail(null)} onResolve={setConfirm}/>}
    {confirm && <ConfirmDialog title={`Mark report #${confirm.id} as resolved?`} confirmLabel="Mark resolved" onCancel={() => setConfirm(null)}
      onConfirm={() => s.changeStatus(confirm.id, "Resolved", note.trim() || undefined).then(ok => { if (ok) { setConfirm(null); setNote(""); } })}>
      <p><strong>{confirm.title}</strong></p>
      <p className="muted">The reporter sees this status on their tracking page. If the photo showed a hazard, confirm it is safe first.</p>
      <label className="field">Resolution note (optional)
        <textarea rows="3" maxLength="2000" value={note} onChange={e => setNote(e.target.value)} placeholder="What was repaired or replaced?"/>
      </label>
    </ConfirmDialog>}
  </section>;
}

function StaffDashboard({s, onOpen}) {
  const user = s.user;
  const overdueCount = s.staffIssues.filter(i => overdueOf(i, targetMap(s.targets)).length).length;
  const d = useMemo(() => {
    const open = s.staffIssues.filter(isOpen);
    return {
      mine: open.filter(i => i.assigned_staff_id === user.id).length,
      pending: open.filter(i => i.status === "Submitted").length,
      progress: open.filter(i => i.status === "In Progress").length,
      high: open.filter(i => i.priority === "High"),
      resolved: s.staffIssues.filter(i => !isOpen(i)).sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5),
    };
  }, [s.staffIssues, user]);
  return <>
    <section className="metrics" aria-label="Task summary">
      <Metric label="Assigned to you" value={d.mine} note="Open and assigned"/>
      <Metric label="Pending" value={d.pending} note="Not started yet"/>
      <Metric label="In progress" value={d.progress} note="Work started"/>
      <Metric label="High priority" value={d.high.length} note="Open, handle first" tone={d.high.length ? "critical" : ""}/>
      <Metric label="Overdue" value={overdueCount} note="Past a response target" tone={overdueCount ? "warning" : ""}/>
    </section>
    <div className="grid-2">
      <section className="panel">
        <div className="panel-head"><div><h2>High-priority open tasks</h2><p>Oldest first.</p></div><button className="btn btn-ghost btn-sm" onClick={() => onOpen("tasks")}>All tasks<ChevronRight size={14}/></button></div>
        {d.high.length === 0 ? <EmptyState icon={ShieldCheck} title="No high-priority tasks open"/> :
          <ul className="item-list">{[...d.high].sort((a, b) => new Date(a.created_at) - new Date(b.created_at)).slice(0, 6).map(i => <li key={i.id}>
            <div><strong>#{i.id} {i.title}</strong><span>{i.location}</span></div><span className="item-side"><StatusBadge status={displayStatus(i)}/><span className="cell-sub">Open {formatDuration(Date.now() - new Date(i.created_at).getTime())}</span></span>
          </li>)}</ul>}
      </section>
      <section className="panel">
        <div className="panel-head"><div><h2>Latest resolved reports</h2><p>Most recently reported first.</p></div></div>
        {d.resolved.length === 0 ? <EmptyState icon={ListChecks} title="No resolved reports yet"/> :
          <ul className="item-list">{d.resolved.map(i => <li key={i.id}><div><strong>#{i.id} {i.title}</strong><span>{i.department}</span></div><span className="item-side"><StatusBadge status={i.status}/><span className="cell-sub">{formatDate(i.created_at)}</span></span></li>)}</ul>}
      </section>
    </div>
  </>;
}

function Team({s}) {
  const [form, setForm] = useState(emptyStaff), [confirm, setConfirm] = useState(null), [reset, setReset] = useState(null), [newPassword, setNewPassword] = useState("");
  return <div className="grid-2 grid-team">
    <section className="panel">
      <div className="panel-head"><div><h2><UserPlus size={18} aria-hidden="true"/> Create staff account</h2><p>The new member signs in with this temporary password.</p></div></div>
      <form className="form-stack" onSubmit={e => { e.preventDefault(); s.addStaff(form).then(ok => ok && setForm(emptyStaff)); }}>
        <label className="field">Full name<input required minLength="2" value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})}/></label>
        <label className="field">Email<input required type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})}/></label>
        <label className="field">Temporary password<input required type="password" minLength="12" value={form.password} onChange={e => setForm({...form, password: e.target.value})}/></label>
        <div className="field-row">
          <label className="field">Department<select value={form.department} onChange={e => setForm({...form, department: e.target.value})}>{DEPARTMENTS.map(d => <option key={d}>{d}</option>)}</select></label>
          <label className="field">Role<select value={form.role} onChange={e => setForm({...form, role: e.target.value})}><option value="staff">Staff</option><option value="admin">Administrator</option></select></label>
        </div>
        <button className="btn btn-primary" disabled={s.busy}>Create account</button>
      </form>
    </section>
    <section className="panel">
      <div className="panel-head"><div><h2>Staff directory</h2><p>{s.staffUsers.length} {s.staffUsers.length === 1 ? "account" : "accounts"}</p></div></div>
      {s.staffUsers.length === 0 ? <EmptyState icon={Users} title="No staff accounts yet">Create the first account with the form.</EmptyState>
      : <div className="table-wrap"><table className="table">
        <thead><tr><th scope="col">Name</th><th scope="col">Department</th><th scope="col">Status</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
        <tbody>{s.staffUsers.map(m => <tr key={m.id}>
          <td data-label="Name"><div className="cell-title"><h3>{m.full_name}</h3><span className="cell-sub">{m.email}{m.role === "admin" ? ", administrator" : ""}</span></div></td>
          <td data-label="Department">{m.department}</td>
          <td data-label="Status"><span className={`badge ${m.is_active ? "badge-status-resolved" : "badge-neutral"}`}>{m.is_active ? "Active" : "Inactive"}</span></td>
          <td data-label="Actions"><div className="row-actions">
            <button className="btn btn-secondary btn-sm" onClick={() => (m.is_active ? setConfirm(m) : s.updateAccountActive(m))} disabled={m.id === s.user.id}>{m.is_active ? "Deactivate" : "Activate"}</button>
            <button className="btn btn-ghost btn-sm" onClick={() => { setNewPassword(""); setReset(m); }}>Reset password</button>
          </div></td>
        </tr>)}</tbody>
      </table></div>}
    </section>
    {confirm && <ConfirmDialog title={`Deactivate ${confirm.full_name}?`} confirmLabel="Deactivate" tone="danger" onCancel={() => setConfirm(null)} onConfirm={() => s.updateAccountActive(confirm).then(() => setConfirm(null))}>
      <p className="muted">They can no longer sign in. Their past status updates are kept. You can activate the account again later.</p>
    </ConfirmDialog>}
    {reset && <ConfirmDialog title={`Reset password for ${reset.full_name}`} confirmLabel="Reset password" onCancel={() => setReset(null)} onConfirm={() => s.resetPassword(reset, newPassword).then(ok => ok && setReset(null))}>
      <label className="field">New password (at least 12 characters)<input type="password" minLength="12" value={newPassword} onChange={e => setNewPassword(e.target.value)} autoComplete="new-password"/></label>
      {s.error && <p className="inline-error" role="alert">{s.error}</p>}
    </ConfirmDialog>}
  </div>;
}

function Account({s}) {
  const [current, setCurrent] = useState(""), [next, setNext] = useState("");
  const u = s.user;
  return <section className="panel account-panel">
    <div className="panel-head"><div><h2>Your account</h2><p>Changing your password signs you out.</p></div></div>
    <dl className="detail-grid"><div><dt>Email</dt><dd>{u.email}</dd></div><div><dt>Department</dt><dd>{u.department}</dd></div><div><dt>Role</dt><dd>{u.role === "admin" ? "Administrator" : "Staff"}</dd></div></dl>
    <form className="form-stack" onSubmit={e => { e.preventDefault(); s.updateOwnPassword(current, next); }}>
      <label className="field">Current password<input type="password" required value={current} onChange={e => setCurrent(e.target.value)} autoComplete="current-password"/></label>
      <label className="field">New password (minimum 12 characters)<input type="password" required minLength="12" value={next} onChange={e => setNext(e.target.value)} autoComplete="new-password"/></label>
      <button className="btn btn-primary" disabled={s.busy}>Update password</button>
    </form>
  </section>;
}

/**
 * Staff workspace. In the app, App owns the session and the sidebar selects `section`.
 * Rendered on its own (as in tests) it creates its own session and shows section tabs.
 */
export default function Staff({issues, live, onUpdate, session, section, onSectionChange}) {
  const own = useStaffSession({issues, onUpdate, enabled: !session});
  const s = session || own;
  const [tabState, setTabState] = useState(null);
  const user = s.user;
  const standalone = section === undefined;
  const active = standalone ? (tabState || (user?.role === "admin" ? "overview" : "tasks")) : section;
  const go = k => (onSectionChange ? onSectionChange(k) : setTabState(k));
  useEffect(() => { if (!user) setTabState(null); }, [user]);

  if (!live) return <section className="panel"><EmptyState icon={LockKeyhole} title="Staff sign-in needs the campus server">The backend is not reachable, so protected tasks cannot load. Reports shown elsewhere are demo records.</EmptyState></section>;
  if (!s.authReady && !user) return <section className="panel"><SkeletonRows rows={3}/></section>;
  if (!user) return <SignIn s={s}/>;

  const isAdmin = user.role === "admin";
  const tabs = isAdmin ? [["overview", "Overview", LayoutDashboard], ["tasks", "Tasks", ListChecks], ["team", "Team", Users], ["account", "Account", KeyRound]] : [["tasks", "Tasks", ListChecks], ["account", "Account", KeyRound]];
  const adminOnly = ["overview", "analytics", "recurring", "escalations", "team"];
  const view = adminOnly.includes(active) && !isAdmin ? "dashboard" : active;

  return <div className="staff">
    {standalone && <div className="staff-bar">
      <div className="staff-identity"><span className="avatar" aria-hidden="true">{user.full_name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()}</span><div><strong>{user.full_name}</strong><span>{isAdmin ? "Administrator, all departments" : user.department}</span></div></div>
      <div className="tabs" role="tablist" aria-label="Staff sections">{tabs.map(([k, l, Icon]) => <button key={k} role="tab" aria-selected={view === k} className={view === k ? "active" : ""} onClick={() => go(k)}><Icon size={16} aria-hidden="true"/>{l}</button>)}</div>
      <button className="btn btn-secondary btn-sm" onClick={() => s.signOut()}><LogOut size={14}/>Sign out</button>
    </div>}
    {s.error && <div className="banner banner-error" role="alert">{s.error}</div>}
    {s.success && <div className="banner banner-ok" role="status">{s.success}</div>}

    {view === "dashboard" && <StaffDashboard s={s} onOpen={go}/>}
    {view === "assigned" && <TaskList s={s} scope="assigned" title="Assigned to you" sub="Open reports an administrator assigned to you."/>}
    {(view === "tasks" || view === "reports") && <TaskList s={s} scope="all" title={isAdmin ? "All reports" : "Department tasks"} sub={isAdmin ? "Every report on campus. Assign, start and resolve from here." : `Reports routed to ${user.department}.`}/>}
    {["overview", "analytics", "recurring", "escalations"].includes(view) && <AdminInsights section={view} issues={s.staffIssues} timings={s.timings} s={s} onOpen={go}/>}
    {view === "team" && <Team s={s}/>}
    {view === "account" && <Account s={s}/>}
  </div>;
}
