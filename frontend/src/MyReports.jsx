import {Bell, CheckCheck, FileText, Plus, RefreshCw, Search} from "lucide-react";
import {CategoryTag, EmptyState, PriorityBadge, SkeletonRows, StatusBadge} from "./components.jsx";
import {formatDate, formatDateTime} from "./ui.js";
import {unreadUpdates} from "./myReports.js";

export function MyReports({reports, loading, onRefresh, onTrack, onReport}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div><h2>My reports</h2><p>Reports submitted from this device. Statuses are loaded live from the campus server.</p></div>
        {reports.length > 0 && <button className="btn btn-secondary btn-sm" onClick={onRefresh}><RefreshCw size={14}/>Refresh</button>}
      </div>
      {loading ? <SkeletonRows rows={3}/>
      : reports.length === 0
        ? <EmptyState icon={FileText} title="No reports from this device yet" action={<button className="btn btn-primary" onClick={onReport}><Plus size={16}/>Create a report</button>}>
            After you submit a report, it appears here so you can follow it without an account. If you used another device, use Track a report with your code.
          </EmptyState>
        : <div className="table-wrap"><table className="table">
            <thead><tr><th scope="col">Report</th><th scope="col">Department</th><th scope="col">Priority</th><th scope="col">Status</th><th scope="col">Submitted</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
            <tbody>{reports.map(r => <tr key={r.code}>
              <td data-label="Report"><div className="cell-title"><h3>{r.title}</h3><span className="cell-sub code-inline">{r.code}</span></div></td>
              <td data-label="Department">{r.department || "Being assigned"}</td>
              <td data-label="Priority">{r.priority ? <PriorityBadge priority={r.priority}/> : "Not loaded"}</td>
              <td data-label="Status">{r.last_status ? <StatusBadge status={r.last_status}/> : "Not loaded"}</td>
              <td data-label="Submitted">{formatDate(r.submitted_at)}</td>
              <td data-label="Actions"><button className="btn btn-ghost btn-sm" onClick={() => onTrack(r.code)}><Search size={14}/>Track</button></td>
            </tr>)}</tbody>
          </table></div>}
    </section>
  );
}

export function Notifications({reports, onMarkRead, onTrack, compact = false}) {
  const updates = unreadUpdates(reports);
  const list = (
    <ul className="notice-list">
      {updates.map(r => {
        const latest = r.history?.[r.history.length - 1];
        return <li key={r.code}>
          <span className="notice-dot" aria-hidden="true"/>
          <div><strong>{r.title}</strong><span>Status changed from {r.seen_status} to {r.last_status}{latest ? `, ${formatDateTime(latest.changed_at)}` : ""}</span></div>
          <button className="btn btn-ghost btn-sm" onClick={() => onTrack(r.code)}>View</button>
        </li>;
      })}
    </ul>
  );
  if (compact) return updates.length ? list : <p className="muted notice-empty">No new updates on your reports.</p>;
  return (
    <section className="panel">
      <div className="panel-head">
        <div><h2>Notifications</h2><p>Status changes on reports submitted from this device.</p></div>
        {updates.length > 0 && <button className="btn btn-secondary btn-sm" onClick={onMarkRead}><CheckCheck size={14}/>Mark all as read</button>}
      </div>
      {updates.length ? list : <EmptyState icon={Bell} title="You are up to date">When staff start or resolve one of your reports, the update appears here.</EmptyState>}
      <p className="field-hint">Email and push notifications are not part of this prototype. Staff escalation alerts are pending (escalation feature).</p>
    </section>
  );
}
