import {useMemo, useState} from "react";
import {MapPin, Wrench} from "lucide-react";

const rank = {high: 0, medium: 1, low: 2};
const departments = ["Electrical Maintenance", "Plumbing Maintenance", "Cleaning Services", "Campus Safety", "Facilities Maintenance", "Campus Administration"];
const level = (p) => rank[(p || "").toLowerCase()] ?? 3;

export default function Staff({issues, live, onUpdate}) {
  const [dept, setDept] = useState("All");

  const tasks = useMemo(() => issues
    .filter(i => !["resolved", "closed"].includes((i.status || "").toLowerCase()))
    .filter(i => dept === "All" || i.department === dept)
    .sort((a, b) => level(a.priority) - level(b.priority) || new Date(a.created_at) - new Date(b.created_at)),
  [issues, dept]);

  return (
    <section className="reports">
      <div className="reports-head">
        <div><h2>Assigned tasks</h2><p>Open reports, most urgent first.</p></div>
        <select className="status-select" style={{maxWidth: 210}} value={dept} onChange={e => setDept(e.target.value)} aria-label="Filter by department">
          <option>All</option>
          {departments.map(d => <option key={d}>{d}</option>)}
        </select>
      </div>
      <div className="toolbar"><span>{tasks.length} open tasks</span></div>
      <div className="issue-list">
        {tasks.map(i => (
          <article className="issue-row" key={i.id}>
            <div className="issue-main">
              <div className="issue-title-line">
                <h3>{i.title}</h3>
                <span className={`priority priority-${(i.priority || "Medium").toLowerCase()}`}>{i.priority} priority</span>
                <span className={`status status-${(i.status || "").toLowerCase().replaceAll(" ", "-")}`}>{i.status}</span>
              </div>
              <p>{i.description}</p>
              <div className="meta">
                <span><MapPin size={14}/>{i.location}</span>
                <span><Wrench size={14}/>{i.department || "Department pending"}</span>
              </div>
            </div>
            <div className="issue-side" style={{gap: 6}}>
              {live && typeof i.id === "number" ? (
                <>
                  {i.status === "Submitted" && <button className="btn btn-light" onClick={() => onUpdate(i.id, "In Progress")}>Start work</button>}
                  <button className="btn btn-primary" onClick={() => onUpdate(i.id, "Resolved")}>Mark resolved</button>
                </>
              ) : <span className="category">Demo record</span>}
            </div>
          </article>
        ))}
      </div>
      {tasks.length === 0 && <div className="empty">No open tasks. New reports will appear here.</div>}
    </section>
  );
}

