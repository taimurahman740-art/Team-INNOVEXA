import {useEffect, useRef, useState} from "react";
import {AlertTriangle, CheckCircle2, X} from "lucide-react";
import {MATCH_STRENGTH, categoryName, toneOf} from "./ui.js";

export function PriorityBadge({priority}) {
  const p = priority || "Medium";
  return <span className={`badge badge-priority-${toneOf(p)}`}><i aria-hidden="true"/>{p} priority</span>;
}

export function StatusBadge({status}) {
  return <span className={`badge badge-status-${toneOf(status)}`}>{status || "Unknown"}</span>;
}

export function SeverityBadge({severity, label = "severity"}) {
  const s = severity || "Low";
  return <span className={`badge badge-severity-${toneOf(s)}`}>{s === "High" && <AlertTriangle size={13} aria-hidden="true"/>}{s} {label}</span>;
}

export function CategoryTag({category}) {
  return <span className="tag">{categoryName(category)}</span>;
}

/** Label that marks AI output as a suggestion, never a confirmed finding. */
export function AiTag({children = "AI suggestion"}) {
  return <span className="ai-tag">{children}</span>;
}

export function Metric({label, value, note, tone, pending}) {
  return (
    <div className={`metric ${tone ? `metric-${tone}` : ""} ${pending ? "metric-pending" : ""}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {note && <span className="metric-note">{note}</span>}
    </div>
  );
}

export function EmptyState({icon: Icon, title, children, action}) {
  return (
    <div className="empty-state">
      {Icon && <div className="empty-icon"><Icon size={22} aria-hidden="true"/></div>}
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

/** Shown instead of a fake result for a capability the backend does not have yet. */
export function PendingNotice({title, children}) {
  return <div className="pending-notice"><span className="badge badge-neutral">Pending</span><div><strong>{title}</strong>{children && <p>{children}</p>}</div></div>;
}

export function SkeletonRows({rows = 4}) {
  return (
    <div className="skeleton-list" aria-hidden="true">
      {Array.from({length: rows}, (_, k) => <div className="skeleton-row" key={k}><span/><span/><span/></div>)}
    </div>
  );
}

export function StrengthIndicator({strength}) {
  const s = MATCH_STRENGTH[strength] || MATCH_STRENGTH.moderate;
  return (
    <span className={`strength strength-${strength || "moderate"}`}>
      <span className="strength-bars" aria-hidden="true">{[1, 2, 3].map(n => <i key={n} className={n <= s.level ? "on" : ""}/>)}</span>
      {s.label}
    </span>
  );
}

export function Toast({message, onClose}) {
  useEffect(() => {
    if (!message) return undefined;
    const t = setTimeout(onClose, 5000);
    return () => clearTimeout(t);
  }, [message, onClose]);
  if (!message) return null;
  return (
    <div className="toast" role="status">
      <CheckCircle2 size={18} aria-hidden="true"/>
      <span>{message}</span>
      <button type="button" className="icon-btn" onClick={onClose} aria-label="Dismiss notification"><X size={16}/></button>
    </div>
  );
}

/** Modal confirmation. Escape or Cancel closes without acting. */
export function ConfirmDialog({title, children, confirmLabel, tone = "primary", onConfirm, onCancel, busy}) {
  const cancelRef = useRef(null);
  const cancel = useRef(onCancel);
  cancel.current = onCancel;
  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = e => { if (e.key === "Escape") cancel.current(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div className="dialog-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onCancel(); }}>
      <section className="dialog dialog-small" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title">
        <header className="dialog-head"><div><h2 id="confirm-title">{title}</h2></div></header>
        <div className="dialog-text">{children}</div>
        <footer className="dialog-foot dialog-foot-end">
          <button type="button" ref={cancelRef} className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button type="button" className={`btn btn-${tone}`} onClick={onConfirm} disabled={busy}>{confirmLabel}</button>
        </footer>
      </section>
    </div>
  );
}

/** Horizontal bars with direct value labels. One hue; `tone` per row only for status meaning. */
export function BarList({rows, empty = "No data yet.", format = v => v, label}) {
  const [hover, setHover] = useState(null);
  if (!rows.length || rows.every(r => !r.value)) return <p className="chart-empty">{empty}</p>;
  const max = Math.max(...rows.map(r => r.value), 1);
  const total = rows.reduce((a, r) => a + r.value, 0);
  return (
    <ul className="bar-list" aria-label={label}>
      {rows.map(r => (
        <li key={r.name} onMouseEnter={() => setHover(r.name)} onMouseLeave={() => setHover(null)} tabIndex={0} onFocus={() => setHover(r.name)} onBlur={() => setHover(null)}
          aria-label={`${r.name}: ${format(r.value)}`}>
          <span className="bar-name">{r.name}</span>
          <span className="bar-track"><span className={`bar-fill ${r.tone ? `bar-${r.tone}` : ""}`} style={{width: `${(r.value / max) * 100}%`}}/></span>
          <span className="bar-value">{format(r.value)}</span>
          {hover === r.name && total > 0 && r.share !== false && <span className="chart-tip" role="tooltip">{r.name}: {format(r.value)} ({Math.round((r.value / total) * 100)}% of total)</span>}
        </li>
      ))}
    </ul>
  );
}

/** Vertical columns for counts over time, with a hover/focus tooltip per column. */
export function ColumnChart({points, label}) {
  const [active, setActive] = useState(null);
  const peak = Math.max(...points.map(p => p.count), 1);
  if (points.every(p => !p.count)) return <p className="chart-empty">No reports in this period.</p>;
  // Round the axis up to an even number so the three ticks are whole, evenly spaced counts.
  const max = peak <= 2 ? 2 : peak <= 4 ? 4 : Math.ceil(peak / 4) * 4;
  const ticks = [max, max / 2, 0];
  return (
    <div className="column-chart" role="img" aria-label={`${label}: ${points.map(p => `${p.label} ${p.count}`).join(", ")}`}>
      <div className="column-axis" aria-hidden="true">{ticks.map(t => <span key={t} style={{bottom: `${(t / max) * 100}%`}}>{t}</span>)}</div>
      <div className="column-plot">
        {ticks.map(t => <i key={t} className="gridline" style={{bottom: `${(t / max) * 100}%`}} aria-hidden="true"/>)}
        {points.map((p, k) => (
          <div className="column" key={p.label} onMouseEnter={() => setActive(k)} onMouseLeave={() => setActive(null)} tabIndex={0} onFocus={() => setActive(k)} onBlur={() => setActive(null)}>
            <span className="column-bar" style={{height: `${(p.count / max) * 100}%`}}/>
            {active === k && <span className="chart-tip column-tip" role="tooltip">Week of {p.label}: {p.count} {p.count === 1 ? "report" : "reports"}</span>}
            <span className="column-label">{p.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
