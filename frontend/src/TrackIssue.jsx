import {useEffect,useState} from "react";
import {Search,Clock3,CheckCircle2} from "lucide-react";
import {getIssueTracking} from "./api.js";

export default function TrackIssue({initialCode=""}) {
 const [code,setCode]=useState(initialCode);
 const [result,setResult]=useState(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 async function lookup(value=code) {
  const normalized=value.trim().toUpperCase();
  if(!normalized){setError("Enter the tracking code you received after submitting your report.");setResult(null);return;}
  setBusy(true);setError("");setResult(null);
  try{setResult(await getIssueTracking(normalized));}
  catch(err){setError(err.message||"Could not find this report. Check the tracking code and try again.");}
  finally{setBusy(false);}
 }
 useEffect(()=>{if(initialCode){setCode(initialCode);lookup(initialCode);}},[initialCode]);
 return <section className="tracking-panel">
  <div className="reports-head"><div><h2>Track your campus report</h2><p>Enter the unique code provided when you submitted your report.</p></div><Clock3 size={22} color="#39805f"/></div>
  <form className="tracking-form" onSubmit={e=>{e.preventDefault();lookup();}}>
   <input aria-label="Report tracking code" value={code} onChange={e=>setCode(e.target.value)} placeholder="e.g. INX-A1B2C3D4E5F6" autoComplete="off"/>
   <button className="btn btn-primary" disabled={busy}><Search size={15}/>{busy?"Searching…":"Track report"}</button>
  </form>
  {error&&<p className="tracking-error" role="alert">{error}</p>}
  {result&&<div className="tracking-result">
   <div className="tracking-result-head"><div><div className="eyebrow">{result.tracking_code}</div><h3>{result.title}</h3></div><span className={`status status-${result.status.toLowerCase().replaceAll(" ","-")}`}>{result.status}</span></div>
   <div className="meta" style={{marginTop:10}}><span>{result.category}</span><span>{result.department||"Department pending"}</span><span>{result.priority} priority</span></div>
   <div className="tracking-timeline" aria-label="Report progress timeline">
    {result.history.map((event,index)=><div className="tracking-event" key={`${event.changed_at}-${index}`}><strong>{index===result.history.length-1?<><CheckCircle2 size={13} style={{display:"inline",verticalAlign:"middle",marginRight:5}}/>{event.new_status}</>:event.new_status}</strong><span>{new Date(event.changed_at).toLocaleString()}</span></div>)}
   </div>
  </div>}
 </section>;
}
