import {useEffect, useState} from "react";
import {Check, Search} from "lucide-react";
import {getIssueTracking} from "./api.js";
import {CategoryTag, PriorityBadge, StatusBadge} from "./components.jsx";
import {formatDate, formatDateTime, responseTimes} from "./ui.js";

const STEPS = ["Submitted", "In Progress", "Resolved"];

function Stepper({status}) {
  const current = status === "Closed" ? 2 : Math.max(0, STEPS.indexOf(status));
  return (
    <ol className="stepper" aria-label="Report progress">
      {STEPS.map((s, k) => (
        <li key={s} className={k < current ? "done" : k === current ? "current" : ""} aria-current={k === current ? "step" : undefined}>
          <span className="step-dot">{k < current || (k === current && k === 2) ? <Check size={14} aria-hidden="true"/> : k + 1}</span>
          <span className="step-label">{s === "In Progress" ? "In progress" : s}</span>
        </li>
      ))}
    </ol>
  );
}

export default function TrackIssue({initialCode = ""}) {
  const [code, setCode] = useState(initialCode);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function lookup(value = code) {
    const normalized = value.trim().toUpperCase();
    if (!normalized) { setError("Enter the tracking code you received after submitting your report."); setResult(null); return; }
    setBusy(true); setError(""); setResult(null);
    try { setResult(await getIssueTracking(normalized)); }
    catch (err) { setError(err.message || "Could not find this report. Check the tracking code and try again."); }
    finally { setBusy(false); }
  }

  useEffect(() => { if (initialCode) { setCode(initialCode); lookup(initialCode); } }, [initialCode]);
  const times = result ? responseTimes(result.created_at, result.history) : null;

  return (
    <div className="track-layout">
      <section className="panel track-search">
        <div className="panel-head"><div><h2>Find your report</h2><p>Your code starts with INX- and was shown after you submitted.</p></div></div>
        <form className="tracking-form" onSubmit={e => { e.preventDefault(); lookup(); }}>
          <input aria-label="Report tracking code" value={code} onChange={e => setCode(e.target.value)} placeholder="INX-A1B2C3D4E5F6" autoComplete="off" spellCheck="false"/>
          <button className="btn btn-primary" disabled={busy}><Search size={16}/>{busy ? "Searching…" : "Track report"}</button>
        </form>
        {error && <p className="inline-error" role="alert">{error}</p>}
        {busy && <div className="skeleton-line" aria-hidden="true"/>}
      </section>

      {result && <section className="panel tracking-result">
        <div className="tracking-result-head">
          <div><span className="code-label">{result.tracking_code}</span><h2>{result.title}</h2></div>
          <StatusBadge status={result.status}/>
        </div>
        <Stepper status={result.status}/>
        <dl className="detail-grid">
          <div><dt>Category</dt><dd><CategoryTag category={result.category}/></dd></div>
          <div><dt>Department</dt><dd>{result.department || "Being assigned"}</dd></div>
          <div><dt>Priority</dt><dd><PriorityBadge priority={result.priority}/></dd></div>
          <div><dt>Reported</dt><dd>{formatDate(result.created_at)}</dd></div>
          {times.response && <div><dt>Work started after</dt><dd>{times.response}</dd></div>}
          {times.resolution && <div><dt>Resolved after</dt><dd>{times.resolution}</dd></div>}
        </dl>
        <h3 className="section-title">Status history</h3>
        <ol className="timeline" aria-label="Report progress timeline">
          {result.history.map((event, index) => (
            <li key={`${event.changed_at}-${index}`} className={index === result.history.length - 1 ? "latest" : ""}>
              <strong>{event.new_status}</strong>
              <span>{formatDateTime(event.changed_at)}</span>
            </li>
          ))}
        </ol>
      </section>}
    </div>
  );
}
