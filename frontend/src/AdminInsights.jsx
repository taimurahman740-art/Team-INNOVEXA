import {useMemo} from "react";

const categories = ["Electrical", "Plumbing", "Cleaning", "Safety", "Facility", "Other"];
const departments = ["Electrical Maintenance", "Plumbing Maintenance", "Cleaning Services", "Campus Safety", "Facilities Maintenance", "HVAC Maintenance", "IT Infrastructure", "Campus Administration"];
const isOpen = (i) => !["resolved", "closed"].includes((i.status || "").toLowerCase());

function Bars({rows}) {
  const max = Math.max(1, ...rows.map(r => r[1]));
  return (
    <div className="bars">
      {rows.map(([name, n]) => (
        <div className="bar-row" key={name}>
          <span>{name}</span>
          <div className="bar-track"><div className="bar-fill" style={{width: `${(n / max) * 100}%`}}/></div>
          <b>{n}</b>
        </div>
      ))}
    </div>
  );
}

export default function AdminInsights({issues}) {
  const d = useMemo(() => {
    const open = issues.filter(isOpen);
    const groups = {};
    issues.forEach(i => {
      const key = `${(i.location || "").trim().toLowerCase()}|${i.category}`;
      groups[key] = groups[key] || {location: i.location, category: i.category, n: 0};
      groups[key].n += 1;
    });
    return {
      open,
      byCategory: categories.map(c => [c, issues.filter(i => i.category === c).length]).sort((a, b) => b[1] - a[1]),
      byDept: departments.map(x => [x, open.filter(i => i.department === x).length]).sort((a, b) => b[1] - a[1]),
      recurring: Object.values(groups).filter(g => g.n >= 3).sort((a, b) => b.n - a.n),
    };
  }, [issues]);

  const high = d.open.filter(i => (i.priority || "").toLowerCase() === "high").length;

  return (
    <div className="admin-insights">
      <h3>Dashboard</h3>
      <div className="stats">
        <article className="stat"><div className="stat-label">Open issues</div><div className="stat-value">{d.open.length}</div><div className="stat-note">Awaiting resolution</div></article>
        <article className="stat"><div className="stat-label">High priority, open</div><div className="stat-value">{high}</div><div className="stat-note">Needs attention first</div></article>
        <article className="stat"><div className="stat-label">Resolved or closed</div><div className="stat-value">{issues.length - d.open.length}</div><div className="stat-note">Completed reports</div></article>
        <article className="stat"><div className="stat-label">Recurring problems</div><div className="stat-value">{d.recurring.length}</div><div className="stat-note">Same place and type, 3+ reports</div></article>
      </div>
      <div className="two-col">
        <div className="admin-card"><h4>Issues by category</h4><Bars rows={d.byCategory}/></div>
        <div className="admin-card"><h4>Open work by department</h4><Bars rows={d.byDept}/></div>
      </div>
      <div className="admin-card">
        <h4>Recurring problems</h4>
        {d.recurring.length === 0
          ? <p className="staff-hint">No location has the same problem reported three or more times.</p>
          : d.recurring.map(g => <div className="recur" key={g.location + g.category}><strong>{g.location}</strong>: {g.category}, reported {g.n} times</div>)}
      </div>
    </div>
  );
}
