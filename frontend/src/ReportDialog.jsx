import {useEffect, useRef, useState} from "react";
import {AlertTriangle, Building2, Camera, CheckCircle2, Copy, ImagePlus, Search, ShieldCheck, Sparkles, X} from "lucide-react";
import {classifyImage, postIssue} from "./api.js";
import {describeAnalysis, reportPayload} from "./reportForm.js";
import {CATEGORIES, DEPARTMENT_BY_CATEGORY, categoryName} from "./ui.js";
import {AiTag, CategoryTag, PriorityBadge, SeverityBadge, StatusBadge, StrengthIndicator} from "./components.jsx";

const empty = {title: "", description: "", category: "", building: "", floor: "", room: "", equipment: "", image_data: null, image_analysis: null};
const MAX_BYTES = 2 * 1024 * 1024;

function AnalysisPanel({form, state, onUseCategory, onRemove}) {
  const r = form.image_analysis;
  const ready = state.status === "success" && r;
  const department = r?.recommended_department || (r && DEPARTMENT_BY_CATEGORY[r.category]);
  return (
    <div className={`ai-panel ai-${state.status}`}>
      <div className="ai-photo">
        <img src={form.image_data} alt="Selected report attachment"/>
        <button type="button" className="btn btn-secondary btn-sm ai-remove" onClick={onRemove}><X size={14}/>Remove photo</button>
      </div>
      <div className="ai-readout">
        <div className="ai-title"><Sparkles size={16} aria-hidden="true"/><h3>Photo analysis</h3>{ready && <AiTag/>}</div>
        {state.status === "loading" && <div className="ai-loading" role="status"><span className="spinner" aria-hidden="true"/><span>Analyzing photo for issue type and visible hazards…</span><div className="skeleton-line"/><div className="skeleton-line short"/></div>}
        {state.message && state.status !== "loading" && <p className={`ai-message ai-message-${state.status}`} role="status">{state.message}</p>}
        {ready && <>
          <dl className="ai-facts">
            <div><dt>Predicted issue</dt><dd>{categoryName(r.category)}</dd></div>
            <div><dt>Match strength</dt><dd><StrengthIndicator strength={r.match_strength}/></dd></div>
            <div><dt>Visible hazard</dt><dd>{r.hazard ? <span className="hazard-text"><AlertTriangle size={14} aria-hidden="true"/>{r.hazard.label}</span> : <span className="muted"><ShieldCheck size={14} aria-hidden="true"/> None detected</span>}</dd></div>
            <div><dt>Suggested severity</dt><dd>{r.suggested_severity ? <SeverityBadge severity={r.suggested_severity}/> : <span className="muted">{r.hazard ? "Assessed by staff" : "No visible hazard"}</span>}</dd></div>
            <div><dt>Suggested priority</dt><dd>{r.estimated_priority ? <PriorityBadge priority={r.estimated_priority}/> : <span className="muted">Set on submit from your description</span>}</dd></div>
            <div><dt>Department</dt><dd>{department || "Set on submit"}</dd></div>
          </dl>
          {r.top_categories?.length > 1 && <p className="ai-alternatives">Other possibilities: {r.top_categories.slice(1).map(t => categoryName(t.category)).join(", ")}</p>}
          {form.category !== r.category
            ? <button type="button" className="btn btn-secondary btn-sm" onClick={() => onUseCategory(r.category)}><CheckCircle2 size={14}/>Use {categoryName(r.category)} as category</button>
            : <p className="ai-applied"><CheckCircle2 size={14} aria-hidden="true"/>Category set to {categoryName(r.category)}</p>}
        </>}
        <p className="ai-disclaimer">Zero-shot image model (CLIP). Match strength compares the photo with each category description; it is not a measured accuracy. Hazards are confirmed by staff.</p>
      </div>
    </div>
  );
}

function Submitted({issue, onTrack, onClose}) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="submitted">
      <div className="submitted-icon"><CheckCircle2 size={28} aria-hidden="true"/></div>
      <h2 id="report-title">Report submitted</h2>
      <p className="muted">Keep this tracking code to follow progress. It is also saved under My reports on this device.</p>
      <div className="code-box"><code>{issue.tracking_code}</code>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => { navigator.clipboard?.writeText(issue.tracking_code || ""); setCopied(true); }}><Copy size={14}/>{copied ? "Copied" : "Copy code"}</button>
      </div>
      <dl className="detail-grid">
        <div><dt>Issue</dt><dd>{issue.title}</dd></div>
        <div><dt>Category</dt><dd><CategoryTag category={issue.category}/></dd></div>
        <div><dt>Department</dt><dd>{issue.department || "Being assigned"}</dd></div>
        <div><dt>Priority</dt><dd><PriorityBadge priority={issue.priority}/></dd></div>
        <div><dt>Status</dt><dd><StatusBadge status={issue.status}/></dd></div>
        {issue.location && <div><dt>Location</dt><dd>{issue.location}</dd></div>}
      </dl>
      {issue.ai_analysis?.routing_reason && <p className="ai-note">{issue.ai_analysis.routing_reason}</p>}
      {issue.ai_analysis?.duplicates?.matches?.length > 0 && <p className="ai-note duplicate-note">A similar report is already open (#{issue.ai_analysis.duplicates.matches[0].issue_id}). Your report was still submitted. Staff will check whether it is the same problem.</p>}
      <div className="dialog-actions">
        <button type="button" className="btn btn-secondary" onClick={onClose}>Done</button>
        <button type="button" className="btn btn-primary" onClick={() => onTrack(issue.tracking_code)}><Search size={16}/>Track this report</button>
      </div>
    </div>
  );
}

export default function ReportDialog({onClose, onSaved, onTrack}) {
  const [form, setForm] = useState(empty);
  const [analysis, setAnalysis] = useState({status: "idle", message: ""});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [saved, setSaved] = useState(null);
  const firstField = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    firstField.current?.focus();
    const onKey = e => { if (e.key === "Escape") closeRef.current(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const textRequired = !form.image_data || !form.image_analysis || !!form.image_analysis.needs_more_info;

  function handleFile(file) {
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) { setError("Choose a PNG, JPEG or WEBP image."); return; }
    if (file.size > MAX_BYTES) { setError("Choose an image smaller than 2 MB."); return; }
    setError("");
    const reader = new FileReader();
    reader.onload = async () => {
      const imageData = reader.result;
      setForm(old => ({...old, image_data: imageData, image_analysis: null}));
      setAnalysis({status: "loading", message: ""});
      try {
        const result = await classifyImage(imageData);
        setForm(old => ({
          ...old, image_analysis: result,
          title: old.title || (result.needs_more_info ? "" : result.suggested_title || ""),
          description: old.description || (result.needs_more_info ? "" : result.suggested_description || ""),
        }));
        setAnalysis(describeAnalysis(result));
      } catch (err) {
        setAnalysis({status: "unavailable", message: `${err.message || "Image recognition is unavailable."} Describe the issue and choose a category instead.`});
      }
    };
    reader.readAsDataURL(file);
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const item = await postIssue(reportPayload(form));
      onSaved(item);
      setSaved(item);
    } catch (err) {
      setError(err?.message && /photo|title|description/i.test(err.message) ? err.message : "Could not save the report. Check that the campus server is reachable, then try again.");
    } finally {
      setBusy(false);
    }
  }

  const set = key => e => setForm({...form, [key]: e.target.value});

  return (
    <div className="dialog-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
      <section className={`dialog ${saved ? "dialog-small" : ""}`} role="dialog" aria-modal="true" aria-labelledby="report-title">
        {saved ? <Submitted issue={saved} onClose={onClose} onTrack={onTrack}/> : <>
        <header className="dialog-head">
          <div><h2 id="report-title">Report an issue</h2><p>Add a photo, a description, or both. Staff review every report.</p></div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={20}/></button>
        </header>
        <form onSubmit={submit} className="dialog-form">
          <div className="dialog-body">
            <section className="report-photo" aria-label="Photo">
              {!form.image_data
                ? <label className={`dropzone ${dragging ? "dragging" : ""}`}
                    onDragOver={e => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files?.[0]); }}>
                    <span className="dropzone-icon"><ImagePlus size={24} aria-hidden="true"/></span>
                    <strong>Attach a photo</strong>
                    <span>A clear photo can be enough on its own. INNOVEXA suggests the issue, hazard, priority and department for you to review.</span>
                    <span className="dropzone-hint"><Camera size={14} aria-hidden="true"/>PNG, JPEG or WEBP, up to 2 MB</span>
                    <input className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { handleFile(e.target.files?.[0]); e.target.value = ""; }}/>
                  </label>
                : <AnalysisPanel form={form} state={analysis}
                    onUseCategory={c => setForm(old => ({...old, category: c}))}
                    onRemove={() => { setForm(old => ({...old, image_data: null, image_analysis: null})); setAnalysis({status: "idle", message: ""}); }}/>}
            </section>
            <section className="report-fields" aria-label="Report details">
              <label className="field">Issue title
                <input ref={firstField} required={textRequired} minLength="3" maxLength="120" value={form.title} onChange={set("title")} placeholder="e.g. Broken classroom light"/>
              </label>
              <label className="field">Description
                <textarea required={textRequired} minLength="5" maxLength="3000" rows="4" value={form.description} onChange={set("description")} placeholder={textRequired ? "What is wrong, and is anyone at risk?" : "Filled from the photo. Edit anything that is wrong."}/>
              </label>
              <label className="field">Category
                <select value={form.category} onChange={set("category")}>
                  <option value="">Auto-detect (recommended)</option>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c === "HVAC" ? "HVAC (heating and cooling)" : categoryName(c)}</option>)}
                </select>
              </label>
              <fieldset className="location-fields">
                <legend><Building2 size={15} aria-hidden="true"/>Location</legend>
                <label className="field field-wide">Building
                  <input required minLength="2" maxLength="80" value={form.building} onChange={set("building")} placeholder="e.g. Engineering Building"/>
                </label>
                <label className="field">Floor
                  <input maxLength="20" value={form.floor} onChange={set("floor")} placeholder="e.g. 2"/>
                </label>
                <label className="field">Room or area
                  <input maxLength="40" value={form.room} onChange={set("room")} placeholder="e.g. 204"/>
                </label>
                <label className="field field-wide">Equipment <span className="optional">optional</span>
                  <input maxLength="80" value={form.equipment} onChange={set("equipment")} placeholder="e.g. Projector, air conditioner"/>
                </label>
              </fieldset>
              {error && <div className="inline-error" role="alert"><AlertTriangle size={16} aria-hidden="true"/>{error}</div>}
            </section>
          </div>
          <footer className="dialog-foot">
            <p>For immediate danger, contact campus security directly.</p>
            <div className="dialog-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" disabled={busy || analysis.status === "loading"}>{busy ? "Saving…" : "Submit report"}</button>
            </div>
          </footer>
        </form>
        </>}
      </section>
    </div>
  );
}
