import {useMemo, useState} from "react";
import {AlertTriangle, ChevronRight, RefreshCw, Repeat, ShieldCheck, Siren} from "lucide-react";
import {BarList, ColumnChart, EmptyState, Metric, PendingNotice, PriorityBadge, StatusBadge} from "./components.jsx";
import {CATEGORIES, DEPARTMENTS, buildingOf, categoryName, displayStatus, formatDateTime, formatDuration, isOpen, overdueOf, targetMap, timeAgo, weeklyCounts} from "./ui.js";

const RECURRING_MIN = 2;
const age = i => Date.now() - new Date(i.created_at).getTime();
const seconds = v => (v == null ? null : formatDuration(v * 1000));

// Status of the eight approved features, as implemented in this build.
const FEATURES = [
  ["Administrator analytics and recurring problems", "live", "This dashboard"],
  ["Automatic escalation and response-time management", "live", "Configurable targets, overdue detection, admin alerts and history"],
  ["Maintenance dashboard and student tracking", "live", "Staff tasks and tracking codes"],
  ["Automatic department routing", "live", "Category to department, with reason shown"],
  ["Machine-learning priority prediction", "partial", "Random Forest baseline with a safety floor; resolution-time feature pending"],
  ["Computer-vision hazard detection and severity", "live", "Zero-shot CLIP, confirmed by staff"],
  ["Duplicate-ticket detection", "live", "Text and photo similarity, flagged for staff review"],
  ["Multimodal vision and text classification", "live", "Photo and description combined; photo-only reports"],
];
const FEATURE_LABEL = {live: "Available", partial: "Partial", pending: "Pending"};

function useStats(issues) {
  return useMemo(() => {
    const open = issues.filter(isOpen);
    const count = (list, key) => {
      const m = new Map();
      list.forEach(i => { const k = key(i); m.set(k, (m.get(k) || 0) + 1); });
      return [...m.entries()].map(([name, value]) => ({name, value})).sort((a, b) => b.value - a.value);
    };
    const groups = (key) => {
      const m = new Map();
      issues.forEach(i => { const k = key(i); const g = m.get(k.id) || {...k, n: 0, open: 0, ids: []}; g.n += 1; g.open += isOpen(i) ? 1 : 0; g.ids.push(i.id); m.set(k.id, g); });
      return [...m.values()].filter(g => g.n >= RECURRING_MIN).sort((a, b) => b.n - a.n);
    };
    const now = Date.now(), week = 7 * 86400000;
    const trend = CATEGORIES.map(c => {
      const list = issues.filter(i => i.category === c);
      const recent = list.filter(i => now - new Date(i.created_at) < 4 * week).length;
      const before = list.filter(i => { const d = now - new Date(i.created_at); return d >= 4 * week && d < 8 * week; }).length;
      return {category: c, recent, before};
    }).filter(t => t.recent || t.before);
    return {
      open, critical: open.filter(i => i.priority === "High").sort((a, b) => age(b) - age(a)),
      byCategory: count(issues, i => categoryName(i.category)),
      byBuilding: count(issues, buildingOf).slice(0, 8),
      byPriority: ["High", "Medium", "Low"].map(p => ({name: p, value: issues.filter(i => i.priority === p).length, tone: p.toLowerCase()})),
      workload: DEPARTMENTS.map(d => {
        const list = open.filter(i => i.department === d);
        return {department: d, open: list.length, high: list.filter(i => i.priority === "High").length, progress: list.filter(i => i.status === "In Progress").length, oldest: list.length ? Math.max(...list.map(age)) : null};
      }).filter(w => w.open).sort((a, b) => b.open - a.open),
      buildingRecurring: groups(i => ({id: `${buildingOf(i).toLowerCase()}|${i.category}`, place: buildingOf(i), category: i.category})),
      locationRecurring: groups(i => ({id: `${(i.location || "").trim().toLowerCase()}|${i.category}`, place: i.location, category: i.category})),
      trend,
    };
  }, [issues]);
}

function Overview({issues, d, timings, s, onOpen}) {
  const resolved = issues.length - d.open.length;
  const avg = timings ? seconds(timings.resolution.average_seconds) : null;
  return <>
    <section className="metrics metrics-6" aria-label="Campus summary">
      <Metric label="Total reports" value={issues.length} note="All time"/>
      <Metric label="Open" value={d.open.length} note="Awaiting resolution"/>
      <Metric label="Resolved" value={resolved} note="Resolved or closed"/>
      <Metric label="Critical open" value={d.critical.length} note="High priority, unresolved" tone={d.critical.length ? "critical" : ""}/>
      <Metric label="Overdue" value={d.open.filter(i => overdueOf(i, targetMap(s?.targets)).length).length} note="Past a response target" tone={d.open.some(i => overdueOf(i, targetMap(s?.targets)).length) ? "warning" : ""}/>
      <Metric label="Avg. resolution" value={avg || "No data"} note={timings ? `From ${timings.resolution.count} resolved with history` : "Loading timing data"}/>
    </section>
    <div className="grid-2 grid-wide-left">
      <section className="panel">
        <div className="panel-head"><div><h2>Reports over time</h2><p>New reports per week, last 8 weeks.</p></div><button className="btn btn-ghost btn-sm" onClick={() => onOpen("analytics")}>Analytics<ChevronRight size={14}/></button></div>
        <ColumnChart points={weeklyCounts(issues, 8)} label="Reports per week"/>
      </section>
      <section className="panel">
        <div className="panel-head"><div><h2>Critical unresolved</h2><p>High priority, oldest first.</p></div><button className="btn btn-ghost btn-sm" onClick={() => onOpen("escalations")}>Escalations<ChevronRight size={14}/></button></div>
        {d.critical.length === 0 ? <EmptyState icon={ShieldCheck} title="No critical reports open"/> :
          <ul className="item-list">{d.critical.slice(0, 5).map(i => <li key={i.id}><div><strong>#{i.id} {i.title}</strong><span>{i.department}</span></div><span className="item-side"><StatusBadge status={displayStatus(i)}/><span className="cell-sub">Open {formatDuration(age(i))}</span></span></li>)}</ul>}
      </section>
    </div>
    <section className="panel">
      <div className="panel-head"><div><h2>Capabilities in this build</h2><p>The eight approved features and their current state. Pending features show no results anywhere in the app.</p></div></div>
      <ul className="feature-list">{FEATURES.map(([name, state, note], k) => <li key={name}><span className="feature-num">{k + 1}</span><div><strong>{name}</strong><span>{note}</span></div><span className={`badge badge-feature-${state}`}>{FEATURE_LABEL[state]}</span></li>)}</ul>
    </section>
  </>;
}

function Analytics({issues, d, timings}) {
  if (!issues.length) return <section className="panel"><EmptyState icon={AlertTriangle} title="No reports to analyse yet">Charts appear once reports are submitted.</EmptyState></section>;
  return <>
    <section className="panel">
      <div className="panel-head"><div><h2>Reports over time</h2><p>New reports per week, last 12 weeks.</p></div></div>
      <ColumnChart points={weeklyCounts(issues, 12)} label="Reports per week"/>
    </section>
    <div className="grid-2">
      <section className="panel"><div className="panel-head"><div><h2>Issues by category</h2><p>All reports.</p></div></div><BarList rows={d.byCategory} label="Issues by category"/></section>
      <section className="panel"><div className="panel-head"><div><h2>Issues by building</h2><p>Top 8 buildings. Older reports use the first part of the location.</p></div></div><BarList rows={d.byBuilding} label="Issues by building"/></section>
      <section className="panel"><div className="panel-head"><div><h2>Priority distribution</h2><p>All reports.</p></div></div><BarList rows={d.byPriority} label="Priority distribution"/></section>
      <section className="panel">
        <div className="panel-head"><div><h2>Resolution performance</h2><p>Average time from report to resolved, from status history.</p></div></div>
        {!timings ? <p className="chart-empty">Timing data is loading or unavailable.</p>
        : <>
          <div className="timing-row">
            <div><span>Time to start work</span><b>{seconds(timings.response.average_seconds) || "No data"}</b><small>{timings.response.count} reports, median {seconds(timings.response.median_seconds) || "n/a"}</small></div>
            <div><span>Time to resolve</span><b>{seconds(timings.resolution.average_seconds) || "No data"}</b><small>{timings.resolution.count} reports, median {seconds(timings.resolution.median_seconds) || "n/a"}</small></div>
          </div>
          <BarList rows={timings.resolution_by_department.map(r => ({name: r.department, value: Math.round(r.average_seconds / 3600 * 10) / 10, share: false}))} format={v => `${v} h`} empty="No resolved reports with history yet." label="Average resolution hours by department"/>
        </>}
      </section>
    </div>
    <section className="panel">
      <div className="panel-head"><div><h2>Department workload</h2><p>Open reports per department.</p></div></div>
      {d.workload.length === 0 ? <EmptyState icon={ShieldCheck} title="No open work"/> :
      <div className="table-wrap"><table className="table">
        <thead><tr><th scope="col">Department</th><th scope="col" className="num">Open</th><th scope="col" className="num">High priority</th><th scope="col" className="num">In progress</th><th scope="col">Oldest open</th></tr></thead>
        <tbody>{d.workload.map(w => <tr key={w.department}><td data-label="Department"><strong>{w.department}</strong></td><td data-label="Open" className="num">{w.open}</td><td data-label="High priority" className="num">{w.high}</td><td data-label="In progress" className="num">{w.progress}</td><td data-label="Oldest open">{formatDuration(w.oldest)}</td></tr>)}</tbody>
      </table></div>}
    </section>
  </>;
}

function RecurringTable({rows, placeLabel}) {
  if (!rows.length) return <EmptyState icon={Repeat} title="No repeats found">{`No ${placeLabel.toLowerCase()} has the same category reported ${RECURRING_MIN} or more times.`}</EmptyState>;
  return <div className="table-wrap"><table className="table">
    <thead><tr><th scope="col">{placeLabel}</th><th scope="col">Category</th><th scope="col" className="num">Reports</th><th scope="col" className="num">Still open</th><th scope="col">Report IDs</th></tr></thead>
    <tbody>{rows.map(g => <tr key={g.id}><td data-label={placeLabel}><strong>{g.place}</strong></td><td data-label="Category">{categoryName(g.category)}</td><td data-label="Reports" className="num">{g.n}</td><td data-label="Still open" className="num">{g.open}</td><td data-label="Report IDs" className="cell-sub">{g.ids.map(id => `#${id}`).join(", ")}</td></tr>)}</tbody>
  </table></div>;
}

function Recurring({d}) {
  return <>
    <div className="grid-2">
      <section className="panel"><div className="panel-head"><div><h2>Most reported categories</h2><p>All reports.</p></div></div><BarList rows={d.byCategory} label="Most reported categories"/></section>
      <section className="panel">
        <div className="panel-head"><div><h2>Category trend</h2><p>Last 4 weeks compared with the 4 weeks before.</p></div></div>
        {d.trend.length === 0 ? <p className="chart-empty">No reports in the last 8 weeks.</p> :
        <div className="table-wrap"><table className="table">
          <thead><tr><th scope="col">Category</th><th scope="col" className="num">Previous 4 weeks</th><th scope="col" className="num">Last 4 weeks</th><th scope="col">Change</th></tr></thead>
          <tbody>{d.trend.map(t => <tr key={t.category}><td data-label="Category">{categoryName(t.category)}</td><td data-label="Previous 4 weeks" className="num">{t.before}</td><td data-label="Last 4 weeks" className="num">{t.recent}</td><td data-label="Change">{t.recent > t.before ? `Up ${t.recent - t.before}` : t.recent < t.before ? `Down ${t.before - t.recent}` : "No change"}</td></tr>)}</tbody>
        </table></div>}
      </section>
    </div>
    <section className="panel"><div className="panel-head"><div><h2>Buildings with recurring problems</h2><p>Same building and category reported {RECURRING_MIN} or more times.</p></div></div><RecurringTable rows={d.buildingRecurring} placeLabel="Building"/></section>
    <section className="panel"><div className="panel-head"><div><h2>Repeated locations</h2><p>Same exact location and category reported {RECURRING_MIN} or more times.</p></div></div><RecurringTable rows={d.locationRecurring} placeLabel="Location"/></section>
  </>;
}

function TargetsForm({s}) {
  const current = targetMap(s.targets);
  const [rows, setRows] = useState(null);
  const data = rows || ["High", "Medium", "Low"].map(p => ({priority: p, ...current[p]}));
  const set = (k, field, value) => setRows(data.map((r, i) => (i === k ? {...r, [field]: value} : r)));
  const hours = m => Math.round(m / 6) / 10;
  const invalid = data.some(r => !(r.start_within_minutes >= 15 && r.resolve_within_minutes >= r.start_within_minutes && r.resolve_within_minutes <= 43200));
  return <section className="panel">
    <div className="panel-head"><div><h2>Response targets</h2><p>How fast each priority must be started and resolved. Auto-escalate raises an alert to administrators when a target is missed.</p></div></div>
    <form className="targets-form" onSubmit={async e => { e.preventDefault(); if (await s.saveTargets(data.map(({priority, start_within_minutes, resolve_within_minutes, auto_escalate}) => ({priority, start_within_minutes, resolve_within_minutes, auto_escalate})))) setRows(null); }}>
      <div className="table-wrap"><table className="table">
        <thead><tr><th scope="col">Priority</th><th scope="col">Start within (hours)</th><th scope="col">Resolve within (hours)</th><th scope="col">Auto-escalate</th></tr></thead>
        <tbody>{data.map((r, k) => <tr key={r.priority}>
          <td data-label="Priority"><PriorityBadge priority={r.priority}/></td>
          <td data-label="Start within (hours)"><input className="input-num" type="number" min="0.25" max="720" step="0.25" aria-label={`${r.priority}: start within hours`} value={hours(r.start_within_minutes)} onChange={e => set(k, "start_within_minutes", Math.round(Number(e.target.value) * 60))}/></td>
          <td data-label="Resolve within (hours)"><input className="input-num" type="number" min="0.25" max="720" step="0.25" aria-label={`${r.priority}: resolve within hours`} value={hours(r.resolve_within_minutes)} onChange={e => set(k, "resolve_within_minutes", Math.round(Number(e.target.value) * 60))}/></td>
          <td data-label="Auto-escalate"><label className="switch"><input type="checkbox" checked={!!r.auto_escalate} onChange={e => set(k, "auto_escalate", e.target.checked)}/><span>{r.auto_escalate ? "On" : "Off"}</span></label></td>
        </tr>)}</tbody>
      </table></div>
      {invalid && <p className="inline-error" role="alert">Each target must be at least 15 minutes, at most 30 days, and resolving cannot be due before starting.</p>}
      <div className="form-actions">
        {rows && <button type="button" className="btn btn-secondary" onClick={() => setRows(null)}>Discard changes</button>}
        <button className="btn btn-primary" disabled={!rows || invalid}>Save targets</button>
      </div>
    </form>
  </section>;
}

function Escalations({d, s}) {
  const targets = targetMap(s?.targets);
  const alerts = (s?.escalations || []).filter(e => !e.acknowledged_at);
  const history = s?.escalations || [];
  // One row per report: list every missed target, rank by the longest overdue.
  const breaches = d.open.map(i => ({issue: i, missed: overdueOf(i, targets)})).filter(r => r.missed.length)
    .map(r => ({...r, overdueMs: Math.max(...r.missed.map(m => m.overdueMs))})).sort((a, b) => b.overdueMs - a.overdueMs);
  const missedText = missed => (missed.length > 1 ? "Not started or resolved in time" : missed[0].kind === "start" ? "Not started in time" : "Not resolved in time");
  return <>
    <section className="metrics" aria-label="Escalation summary">
      <Metric label="Open alerts" value={alerts.length} note="Escalated, not yet acknowledged" tone={alerts.length ? "critical" : ""}/>
      <Metric label="Overdue reports" value={breaches.length} note="Past a response target"/>
      <Metric label="Critical open" value={d.critical.length} note="High priority, unresolved"/>
      <Metric label="Escalations recorded" value={history.length} note="All time"/>
    </section>
    <section className="panel">
      <div className="panel-head"><div><h2>Open alerts</h2><p>Reports escalated to administrators automatically. Acknowledge one once someone is handling it.</p></div><button className="btn btn-secondary btn-sm" onClick={s.checkNow}><RefreshCw size={14}/>Check now</button></div>
      {alerts.length === 0 ? <EmptyState icon={ShieldCheck} title="No open alerts">Every escalated report has been acknowledged, or no report has missed an auto-escalate target.</EmptyState> :
      <ul className="alert-list">{alerts.map(e => <li key={e.id}>
        <Siren size={18} aria-hidden="true"/>
        <div><strong>#{e.issue_id} {e.issue_title}</strong><span>{e.reason} {e.issue_department}. Raised {timeAgo(e.created_at)}.</span></div>
        <button className="btn btn-primary btn-sm" onClick={() => s.acknowledge(e.id)}>Acknowledge</button>
      </li>)}</ul>}
    </section>
    <section className="panel">
      <div className="panel-head"><div><h2>Response-time breaches</h2><p>Open reports past their start or resolve target, any priority, most overdue first.</p></div></div>
      {breaches.length === 0 ? <EmptyState icon={ShieldCheck} title="No overdue reports">Every open report is within its response targets.</EmptyState> :
      <div className="table-wrap"><table className="table">
        <thead><tr><th scope="col">ID</th><th scope="col">Report</th><th scope="col">Priority</th><th scope="col">Missed target</th><th scope="col" className="num">Overdue by</th></tr></thead>
        <tbody>{breaches.map(b => <tr key={b.issue.id}>
          <td data-label="ID" className="cell-id">#{b.issue.id}</td>
          <td data-label="Report"><div className="cell-title"><h3>{b.issue.title}</h3><span className="cell-sub">{b.issue.department}</span></div></td>
          <td data-label="Priority"><PriorityBadge priority={b.issue.priority}/></td>
          <td data-label="Missed target">{missedText(b.missed)}</td>
          <td data-label="Overdue by" className="num">{formatDuration(b.overdueMs)}</td>
        </tr>)}</tbody>
      </table></div>}
    </section>
    <section className="panel">
      <div className="panel-head"><div><h2>Escalation history</h2><p>Every escalation raised, newest first.</p></div></div>
      {history.length === 0 ? <EmptyState icon={Siren} title="No escalations yet">When an auto-escalate report misses its target, it is recorded here.</EmptyState> :
      <div className="table-wrap"><table className="table">
        <thead><tr><th scope="col">Raised</th><th scope="col">Report</th><th scope="col">Reason</th><th scope="col">Acknowledged</th></tr></thead>
        <tbody>{history.map(e => <tr key={e.id}>
          <td data-label="Raised">{formatDateTime(e.created_at)}</td>
          <td data-label="Report"><div className="cell-title"><h3>#{e.issue_id} {e.issue_title}</h3><span className="cell-sub">{displayStatus({status: e.issue_status})}</span></div></td>
          <td data-label="Reason">{e.reason}</td>
          <td data-label="Acknowledged">{e.acknowledged_at ? `${formatDateTime(e.acknowledged_at)} by ${e.acknowledged_by}` : <span className="badge badge-priority-high">Open</span>}</td>
        </tr>)}</tbody>
      </table></div>}
    </section>
    <TargetsForm s={s}/>
  </>;
}

export default function AdminInsights({issues, timings, s, section = "overview", onOpen = () => {}}) {
  const d = useStats(issues);
  if (section === "analytics") return <Analytics issues={issues} d={d} timings={timings}/>;
  if (section === "recurring") return <Recurring d={d}/>;
  if (section === "escalations") return <Escalations d={d} s={s}/>;
  return <Overview issues={issues} d={d} timings={timings} s={s} onOpen={onOpen}/>;
}
