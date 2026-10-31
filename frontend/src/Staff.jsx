import {useMemo, useState} from "react";
import {LockKeyhole, MapPin, Wrench, ShieldCheck} from "lucide-react";

const rank = {high: 0, medium: 1, low: 2};
const departments = ["Electrical Maintenance", "Plumbing Maintenance", "Cleaning Services", "Campus Safety", "Facilities Maintenance", "Campus Administration"];
const level = (p) => rank[(p || "").toLowerCase()] ?? 3;

export default function Staff({issues, live, onUpdate}) {
  const [dept, setDept] = useState("All");
  const [staffKey, setStaffKey] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [keyError, setKeyError] = useState("");
  const tasks = useMemo(() => issues
    .filter(i => !["resolved", "closed"].includes((i.status || "").toLowerCase()))
    .filter(i => dept === "All" || i.department === dept)
    .sort((a, b) => level(a.priority) - level(b.priority) || new Date(a.created_at) - new Date(b.created_at)),
  [issues, dept]);

  async function changeStatus(id, status) {
    try {
      await onUpdate(id, status, staffKey);
      setKeyError("");
      setUnlocked(true);
    } catch (error) {
      setUnlocked(false);
      setKeyError(error.message || "Staff authorization failed.");
    }
  }

  return (
    <section className="reports">
      <div className="reports-head">
        <div><h2>Staff task centre</h2><p>Open reports, ranked by priority. Staff access is protected.</p></div>
        <select className="status-select" style={{maxWidth: 210}} value={dept} onChange={e => setDept(e.target.value)} aria-label="Filter by department">
          <option>All departments</option>
          {departments.map(d => <option key={d}>{d}</option>)}
        </select>
      </div>
      <div className="staff-access">
        <div className="staff-access-title"><ShieldCheck size={18}/><div><strong>Staff authorization</strong><span>Enter the staff key configured by the project administrator.</span></div></div>
        <div className="staff-key-row"><input type="password" value={staffKey} onChange={e => {setStaffKey(e.target.value);setUnlocked(false);setKeyError("");}} placeholder="Staff access key" autoComplete="off"/><button className="btn btn-primary" disabled={!staffKey.trim()} onClick={() => setUnlocked(true)}><LockKeyhole size={14}/>Unlock actions</button></div>
        {keyError && <p className="staff-error">{keyError}</p>}
        {!unlocked && <p className="staff-hint">You can view tasks without a key. A valid key is required to change report statuses.</p>}
      </div>
      <div className="toolbar"><span>{tasks.length} open tasks</span><span>{unlocked ? "Staff key entered" : "View-only mode"}</span></div>
      <div className="issue-list">
        {tasks.map(i => (
          <article className="issue-row" key={i.id}>
            <div className="issue-main">
              <div className="issue-title-line"><h3>{i.title}</h3>
                <span className={`priority priority-${(i.priority || "Medium").toLowerCase()}`}>{i.priority} priority</span>
                <span className={`status status-${(i.status || "").toLowerCase().replaceAll(" ", "-")}`}>{i.status}</span>
              </div>
              <p>{i.description}</p>
              <div className="meta"><span><MapPin size={14}/>{i.location}</span><span><Wrench size={14}/>{i.department || "Department pending"}</span></div>
              {i.image_data && <img className="issue-photo" src={i.image_data} alt="Photo attached to this campus report"/>}
              {typeof i.classification_confidence === "number" && <div className="ai-note">ML category confidence: {(i.classification_confidence * 100).toFixed(0)}% · Please verify before action</div>}
            </div>
            <div className="issue-side" style={{gap: 6}}>
              {live && typeof i.id === "number" ? (
                <>
                  {i.status === "Submitted" && <button className="btn btn-light" disabled={!unlocked} onClick={() => changeStatus(i.id, "In Progress")}>Start work</button>}
                  <button className="btn btn-primary" disabled={!unlocked} onClick={() => changeStatus(i.id, "Resolved")}>Mark resolved</button>
                </>
              ) : <span className="category">Database unavailable</span>}
            </div>
          </article>
        ))}
      </div>
      {tasks.length === 0 && <div className="empty">No open tasks. New reports will appear here.</div>}
    </section>
  );
}
