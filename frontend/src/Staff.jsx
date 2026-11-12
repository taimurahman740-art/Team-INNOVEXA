import {useEffect,useMemo,useState} from "react";
import {LockKeyhole,LogOut,ShieldCheck,UserPlus,Wrench,MapPin} from "lucide-react";
import {assignIssue,bootstrapStaffAdmin,createStaffUser,getIssueHistory,getStaffIssues,getStaffSetupStatus,getStaffUsers,loginStaff} from "./api.js";

const departments=["Electrical Maintenance","Plumbing Maintenance","Cleaning Services","Campus Safety","Facilities Maintenance","Campus Administration"];
const rank={high:0,medium:1,low:2};
const priorityRank=p=>rank[(p||"").toLowerCase()]??3;

export default function Staff({issues,live,onUpdate}) {
  const [setupAvailable,setSetupAvailable]=useState(false),[authReady,setAuthReady]=useState(false),[bootstrapMode,setBootstrapMode]=useState(false);
  const [email,setEmail]=useState(""),[password,setPassword]=useState(""),[bootstrapKey,setBootstrapKey]=useState(""),[fullName,setFullName]=useState("");
  const [token,setToken]=useState(""),[user,setUser]=useState(null),[staffIssues,setStaffIssues]=useState(issues),[staffUsers,setStaffUsers]=useState([]);
  const [error,setError]=useState(""),[success,setSuccess]=useState(""),[busy,setBusy]=useState(false),[view,setView]=useState("open"),[dept,setDept]=useState("All");
  const [history,setHistory]=useState({}),[historyLoading,setHistoryLoading]=useState(null);
  const [newStaff,setNewStaff]=useState({full_name:"",email:"",password:"",department:"Facilities Maintenance",role:"staff"});

  useEffect(()=>{getStaffSetupStatus().then(r=>{setSetupAvailable(r.setup_available);setBootstrapMode(r.setup_available);}).catch(()=>setError("Could not check staff account setup.")).finally(()=>setAuthReady(true));},[]);

  async function loadSession(session) {
    const records=await getStaffIssues(session.access_token);
    const members=session.user.role==="admin"?await getStaffUsers(session.access_token):[];
    setToken(session.access_token);setUser(session.user);setStaffIssues(records);setStaffUsers(members);setError("");
  }
  async function signIn(event) {
    event.preventDefault();setBusy(true);setError("");
    try {
      const session=bootstrapMode
        ? await bootstrapStaffAdmin({bootstrap_key:bootstrapKey,email,full_name:fullName,password,department:"Campus Administration"})
        : await loginStaff(email,password);
      await loadSession(session);
    } catch(err) {setError(err.message||"Staff sign-in failed.");}
    finally {setBusy(false);}
  }
  function signOut(){setToken("");setUser(null);setPassword("");setStaffUsers([]);setStaffIssues(issues);setHistory({});setSuccess("");setError("");}
  async function refresh(){try{setStaffIssues(await getStaffIssues(token));setError("");}catch(err){setError(err.message||"Could not refresh tasks.");}}
  async function changeStatus(id,status){try{const item=await onUpdate(id,status,token);setStaffIssues(old=>old.map(x=>x.id===id?item:x));setSuccess(`Report #${id} updated to ${status}.`);setError("");}catch(err){setError(err.message||"Could not update report.");}}
  async function toggleHistory(id){
    if(history[id]){setHistory(old=>({...old,[id]:null}));return;}
    setHistoryLoading(id);
    try{const rows=await getIssueHistory(id,token);setHistory(old=>({...old,[id]:rows}));}
    catch(err){setError(err.message||"Could not load history.");}
    finally{setHistoryLoading(null);}
  }
  async function addStaff(event){
    event.preventDefault();setBusy(true);setError("");setSuccess("");
    try{await createStaffUser(newStaff,token);setStaffUsers(await getStaffUsers(token));setNewStaff({full_name:"",email:"",password:"",department:"Facilities Maintenance",role:"staff"});setSuccess("Staff account created.");}
    catch(err){setError(err.message||"Could not create account.");}
    finally{setBusy(false);}
  }
  async function assign(id,value){
    try{const item=await assignIssue(id,value?Number(value):null,token);setStaffIssues(old=>old.map(x=>x.id===id?item:x));setSuccess("Task assignment saved.");}
    catch(err){setError(err.message||"Could not assign task.");}
  }
  const tasks=useMemo(()=>staffIssues
    .filter(x=>view==="all"||(view==="resolved"?["resolved","closed"].includes((x.status||"").toLowerCase()):!["resolved","closed"].includes((x.status||"").toLowerCase())))
    .filter(x=>user?.role!=="admin"||dept==="All"||x.department===dept)
    .sort((a,b)=>priorityRank(a.priority)-priorityRank(b.priority)||new Date(a.created_at)-new Date(b.created_at)),[staffIssues,view,dept,user]);

  if(!live)return <section className="reports"><h2>Staff task centre</h2><p>Connect the backend to sign in and load protected tasks.</p></section>;
  if(!authReady)return <section className="reports"><p>Checking staff account setup…</p></section>;
  if(!user)return <section className="reports">
    <div className="reports-head"><div><h2>{bootstrapMode?"Create the first administrator":"Staff sign in"}</h2><p>Each staff member has an individual account and department.</p></div><ShieldCheck size={22}/></div>
    <form className="form staff-login-form" onSubmit={signIn}>
      {bootstrapMode&&<><label>Administrator name<input required value={fullName} onChange={e=>setFullName(e.target.value)}/></label><label>One-time setup key<input required type="password" value={bootstrapKey} onChange={e=>setBootstrapKey(e.target.value)} placeholder="STAFF_BOOTSTRAP_KEY"/></label></>}
      <label>Email<input required type="email" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="username"/></label>
      <label>Password<input required type="password" minLength="12" value={password} onChange={e=>setPassword(e.target.value)} autoComplete={bootstrapMode?"new-password":"current-password"}/></label>
      <button className="btn btn-primary" disabled={busy}><LockKeyhole size={14}/>{busy?"Please wait…":bootstrapMode?"Create administrator":"Sign in"}</button>
    </form>
    {error&&<p className="staff-error" role="alert">{error}</p>}
    {!bootstrapMode&&<p className="staff-hint">The previous shared staff key is no longer accepted. Ask your administrator for an individual account.</p>}
    {setupAvailable&&!bootstrapMode&&<button className="btn btn-light" onClick={()=>setBootstrapMode(true)}>Initial administrator setup</button>}
  </section>;

  return <section className="reports">
    <div className="reports-head"><div><h2>Staff task centre</h2><p>{user.role==="admin"?"Administrator · all departments":user.department+" · department tasks"}</p></div><button className="btn btn-light" onClick={signOut}><LogOut size={14}/>Sign out</button></div>
    <div className="staff-profile"><strong>{user.full_name}</strong><span>{user.email} · {user.role}</span><button className="btn btn-light" onClick={refresh}>Refresh tasks</button></div>
    {error&&<p className="staff-error" role="alert">{error}</p>}{success&&<p className="staff-success" role="status">{success}</p>}
    {user.role==="admin"&&<>
      <div className="staff-admin-panel"><h3><UserPlus size={16}/> Create staff account</h3>
        <form className="form staff-admin-form" onSubmit={addStaff}>
          <label>Full name<input required minLength="2" value={newStaff.full_name} onChange={e=>setNewStaff({...newStaff,full_name:e.target.value})}/></label>
          <label>Email<input required type="email" value={newStaff.email} onChange={e=>setNewStaff({...newStaff,email:e.target.value})}/></label>
          <label>Temporary password<input required type="password" minLength="12" value={newStaff.password} onChange={e=>setNewStaff({...newStaff,password:e.target.value})}/></label>
          <label>Department<select value={newStaff.department} onChange={e=>setNewStaff({...newStaff,department:e.target.value})}>{departments.map(d=><option key={d}>{d}</option>)}</select></label>
          <label>Role<select value={newStaff.role} onChange={e=>setNewStaff({...newStaff,role:e.target.value})}><option value="staff">Staff</option><option value="admin">Administrator</option></select></label>
          <button className="btn btn-primary" disabled={busy}>Create account</button>
        </form>
      </div>
      <div className="staff-admin-panel"><h3>Staff directory</h3>{staffUsers.map(m=><div className="staff-directory-row" key={m.id}><strong>{m.full_name}</strong><span>{m.department} · {m.role} · {m.email}</span></div>)}</div>
    </>}
    <div className="toolbar"><span>{tasks.length} {view==="resolved"?"resolved reports":view==="all"?"reports":"open tasks"}</span><div className="staff-toolbar-controls">
      {user.role==="admin"&&<select className="status-select" value={dept} onChange={e=>setDept(e.target.value)}><option>All</option>{departments.map(d=><option key={d}>{d}</option>)}</select>}
      <button className="btn btn-light" onClick={()=>setView("open")}>Open</button><button className="btn btn-light" onClick={()=>setView("resolved")}>Resolved</button><button className="btn btn-light" onClick={()=>setView("all")}>All</button>
    </div></div>
    <div className="issue-list">{tasks.map(i=><article className="issue-row" key={i.id}>
      <div className="issue-main"><div className="issue-title-line"><h3>{i.title}</h3><span className={`priority priority-${(i.priority||"Medium").toLowerCase()}`}>{i.priority} priority</span><span className={`status status-${(i.status||"").toLowerCase().replaceAll(" ","-")}`}>{i.status}</span></div>
        <p>{i.description}</p><div className="ai-note">Safety triage: {i.risk_level||"Low"} ({i.risk_score??0}/10) {i.risk_reasons?.join("; ")}</div>
        <div className="meta"><span><Wrench size={14}/>{i.department}</span><span><MapPin size={14}/>{i.location}</span><span>{i.assigned_staff_id?"Assigned staff #"+i.assigned_staff_id:"Unassigned"}</span></div>
        {i.image_data&&<img className="issue-photo" src={i.image_data} alt="Report attachment"/>}
        <div className="toolbar"><button className="btn btn-light" disabled={historyLoading===i.id} onClick={()=>toggleHistory(i.id)}>{historyLoading===i.id?"Loading…":history[i.id]?"Hide history":"View history"}</button>
          {user.role==="admin"&&<label className="staff-assignment-control">Assign to<select value={i.assigned_staff_id||""} onChange={e=>assign(i.id,e.target.value)}><option value="">Unassigned</option>{staffUsers.filter(m=>m.is_active&&m.role==="staff"&&m.department===i.department).map(m=><option key={m.id} value={m.id}>{m.full_name}</option>)}</select></label>}
        </div>
        {history[i.id]&&<div className="status-history"><strong>Status history</strong>{history[i.id].map(h=><div key={h.id}>{h.old_status||"Created"} → {h.new_status}<span>{new Date(h.changed_at).toLocaleString()} · {h.changed_by}</span></div>)}</div>}
      </div>
      <div className="issue-side">{i.status==="Submitted"&&<button className="btn btn-light" onClick={()=>changeStatus(i.id,"In Progress")}>Start work</button>}{!["resolved","closed"].includes((i.status||"").toLowerCase())&&<button className="btn btn-primary" onClick={()=>changeStatus(i.id,"Resolved")}>Mark resolved</button>}</div>
    </article>)}</div>
    {!tasks.length&&<div className="empty">No tasks in this view for your account.</div>}
  </section>;
}
