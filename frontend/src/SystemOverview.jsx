import {ArrowRight, Brain, Cloud, Database, Monitor, ShieldCheck, Users} from "lucide-react";

// Every figure on this page comes from the repository: CI runs, app/evaluate_*.py and
// tests/test_duplicates.py. Update it when those results change.

const FEATURES = [
  {n: 1, name: "Administrator analytics and recurring-problem detection", how: "Trends, categories, buildings, priorities, resolution times and department workload from live data. Repeated problems grouped by building and location.", where: [["Analytics", "admin-analytics"], ["Recurring problems", "admin-recurring"]], role: "Admin", status: "Available"},
  {n: 2, name: "Automatic escalation and response-time management", how: "Configurable start and resolve targets per priority. Overdue reports are detected from real timestamps; high-priority misses are escalated to administrators with an alert and history.", where: [["Escalations", "admin-escalations"]], role: "Admin", status: "Available"},
  {n: 3, name: "Maintenance dashboard and student status tracking", how: "Staff dashboards, task queues, status updates with resolution notes. Students track progress with a code, no account needed.", where: [["Track a report", "tracking"], ["Staff dashboard", "staff-dashboard"]], role: "Student, Staff", status: "Available"},
  {n: 4, name: "Automatic maintenance-department routing", how: "Each category maps to a department, including HVAC and IT Infrastructure. The routing reason is stored and shown to staff.", where: [["Report an issue", "report"]], role: "Student", status: "Available"},
  {n: 5, name: "Machine-learning priority prediction", how: "Random Forest on category, safety risk, area traffic and service disruption, with a safety floor. Historical resolution time will be added when enough resolved reports exist.", where: [["Issue details", "staff-tasks"]], role: "Staff", status: "Partial"},
  {n: 6, name: "Computer-vision hazard detection and severity", how: "Zero-shot CLIP checks photos for exposed wiring, water pooling, structural cracks and broken glass. A hazard raises the risk score; staff confirm it on site.", where: [["Report an issue", "report"]], role: "Student", status: "Available"},
  {n: 7, name: "Duplicate-ticket detection", how: "TF-IDF text cosine and photo feature cosine against open reports in the same department or building. Matches are flagged for staff review, never rejected.", where: [["Issue details", "staff-tasks"]], role: "Staff", status: "Available"},
  {n: 8, name: "Multimodal vision and text classification", how: "Photo and description probabilities are combined. A clear photo alone is enough; an unclear one prompts the student for a description.", where: [["Report an issue", "report"]], role: "Student", status: "Available"},
];

const MODELS = [
  {name: "Text classifier", method: "Multinomial Naive Bayes", data: "14 paraphrased Tongmyong board posts and starter phrases", result: "24 of 30 synthetic hold-out reports matched (macro F1 0.84)", limit: "Synthetic hold-out set, not real-world accuracy"},
  {name: "Photo analysis", method: "Zero-shot CLIP (clip-vit-large-patch14)", data: "No training; text prompts per category and hazard", result: "Uncertain photos ask for a description instead of guessing", limit: "Not tuned on campus photos; staff confirm every hazard"},
  {name: "Priority prediction", method: "Random Forest, 200 trees", data: "44 labelled sample reports (30 synthetic)", result: "Accuracy 0.67 vs 0.64 for keyword rules; missed 40 vs 60 High reports of 110 held out", limit: "Tiny, mostly synthetic data; a baseline, not validated"},
  {name: "Duplicate detection", method: "TF-IDF and image-feature cosine similarity", data: "Calibrated on hand-made report and photo pairs", result: "Duplicates 0.27–0.52 vs different 0.00–0.04 (text); same scene 0.71 vs different 0.17 (photo)", limit: "Photo check finds the same scene, not the same kind of fault"},
  {name: "Escalation", method: "Rule engine with configurable targets", data: "Report timestamps and status history", result: "Overdue detection and alerts verified by automated tests", limit: "Runs when staff use the app (no background scheduler on the free hosting tier)"},
];

const STACK = [
  ["Frontend", "React 18, Vite 5, installable PWA with offline notice"],
  ["Backend", "Python, FastAPI, SQLAlchemy"],
  ["Database", "Neon PostgreSQL"],
  ["Machine learning", "scikit-learn, Hugging Face Inference (CLIP), Pillow"],
  ["Hosting", "Render (web service and static site)"],
  ["Quality", "GitHub Actions on every push: 110 backend tests, 19 frontend tests, model evaluations, production build"],
];

const PRINCIPLES = [
  "AI output is a suggestion. Staff review every report, and every photo hazard is confirmed on site.",
  "Safety rules always win: a high safety-risk report is High priority whatever a model predicts.",
  "Nothing is rejected automatically. Possible duplicates are flagged for a person to decide.",
  "Students see match strength in words, not model percentages, because the scores are not calibrated accuracy.",
  "Every chart and count comes from the live database. Unfinished capabilities are labelled, never simulated.",
];

function Flow() {
  const node = (Icon, title, text) => <div className="flow-node"><Icon size={20} aria-hidden="true"/><strong>{title}</strong><span>{text}</span></div>;
  return (
    <div className="flow" role="img" aria-label="Architecture: students, staff and administrators use the React PWA, which calls the FastAPI backend on Render. The backend stores data in Neon PostgreSQL, runs the text, priority, duplicate and escalation models, and calls Hugging Face for photo analysis.">
      {node(Users, "Students, staff, admins", "Phone or desktop browser")}
      <ArrowRight className="flow-arrow" size={20} aria-hidden="true"/>
      {node(Monitor, "INNOVEXA web app", "React PWA on Render")}
      <ArrowRight className="flow-arrow" size={20} aria-hidden="true"/>
      <div className="flow-stack">
        {node(Brain, "FastAPI backend", "Routing, priority model, duplicates, escalation")}
        <div className="flow-row">
          {node(Database, "Neon PostgreSQL", "Reports, history, escalations")}
          {node(Cloud, "Hugging Face", "CLIP photo analysis")}
        </div>
      </div>
    </div>
  );
}

export default function SystemOverview({onOpen}) {
  return <>
    <section className="panel overview-hero">
      <div>
        <h2>AI-Based Hazard and Facility Monitoring System</h2>
        <p>Students report campus facility problems with a photo, a description or both. INNOVEXA classifies the issue, checks the photo for hazards, predicts priority, routes it to the right maintenance team, flags possible duplicates and escalates reports that miss their response targets. Staff and administrators manage the work and monitor campus conditions in one place.</p>
      </div>
      <dl className="overview-facts">
        <div><dt>Approved features</dt><dd>8</dd></div>
        <div><dt>Available</dt><dd>7</dd></div>
        <div><dt>Partial</dt><dd>1</dd></div>
        <div><dt>Automated tests</dt><dd>129</dd></div>
      </dl>
    </section>

    <section className="panel">
      <div className="panel-head"><div><h2>Architecture</h2><p>How a report moves through the system.</p></div></div>
      <Flow/>
    </section>

    <section className="panel">
      <div className="panel-head"><div><h2>The eight approved features</h2><p>What each one does and where to see it. Staff and admin pages need a staff sign-in.</p></div></div>
      <div className="table-wrap"><table className="table features-table">
        <thead><tr><th scope="col">#</th><th scope="col">Feature</th><th scope="col">How it works</th><th scope="col">Where to see it</th><th scope="col">Status</th></tr></thead>
        <tbody>{FEATURES.map(f => <tr key={f.n}>
          <td data-label="#" className="cell-id">{f.n}</td>
          <td data-label="Feature"><div className="cell-title"><h3>{f.name}</h3><span className="cell-sub">{f.role}</span></div></td>
          <td data-label="How it works">{f.how}</td>
          <td data-label="Where to see it"><div className="link-stack">{f.where.map(([label, view]) => <button key={label} className="btn btn-ghost btn-sm" onClick={() => onOpen(view)}>{label}</button>)}</div></td>
          <td data-label="Status"><span className={`badge ${f.status === "Available" ? "badge-feature-live" : "badge-feature-partial"}`}>{f.status}</span></td>
        </tr>)}</tbody>
      </table></div>
    </section>

    <section className="panel">
      <div className="panel-head"><div><h2>AI models and results</h2><p>Measured on the project's own data. Most of it is small or synthetic, so these show the methods work; they are not real-world accuracy.</p></div></div>
      <div className="table-wrap"><table className="table">
        <thead><tr><th scope="col">Model</th><th scope="col">Method</th><th scope="col">Data</th><th scope="col">Result</th><th scope="col">Limitation</th></tr></thead>
        <tbody>{MODELS.map(m => <tr key={m.name}>
          <td data-label="Model"><strong>{m.name}</strong></td>
          <td data-label="Method">{m.method}</td>
          <td data-label="Data">{m.data}</td>
          <td data-label="Result">{m.result}</td>
          <td data-label="Limitation" className="muted">{m.limit}</td>
        </tr>)}</tbody>
      </table></div>
    </section>

    <div className="grid-2">
      <section className="panel">
        <div className="panel-head"><div><h2>Responsible AI</h2><p>Rules the system follows.</p></div></div>
        <ul className="principles">{PRINCIPLES.map(p => <li key={p}><ShieldCheck size={16} aria-hidden="true"/><span>{p}</span></li>)}</ul>
      </section>
      <section className="panel">
        <div className="panel-head"><div><h2>Technology</h2><p>Stack and quality checks.</p></div></div>
        <dl className="stack-list">{STACK.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      </section>
    </div>
  </>;
}
