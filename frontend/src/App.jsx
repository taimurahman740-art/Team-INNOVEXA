import {useCallback, useEffect, useMemo, useRef, useState} from "react";
import {Activity, AlertTriangle, Info, ChartColumn, Bell, ClipboardList, FileText, Inbox, KeyRound, LayoutDashboard, ListChecks, LogIn, LogOut, Menu, Plus, RefreshCw, Repeat, Search, ShieldAlert, ShieldCheck, Siren, UserCheck, Users, WifiOff, X} from "lucide-react";
import {getIssueTracking, getIssues, patchStatus} from "./api.js";
import Staff from "./Staff.jsx";
import TrackIssue from "./TrackIssue.jsx";
import SystemOverview from "./SystemOverview.jsx";
import ReportDialog from "./ReportDialog.jsx";
import {MyReports, Notifications} from "./MyReports.jsx";
import {useStaffSession} from "./staffSession.js";
import {CategoryTag, EmptyState, Metric, PriorityBadge, SkeletonRows, StatusBadge, Toast} from "./components.jsx";
import {formatDate, isOpen, timeAgo} from "./ui.js";
import {loadMyReports, markAllSeen, mergeTracking, rememberReport, saveMyReports, unreadUpdates} from "./myReports.js";

const demo = [
 {id:"demo1",title:"Air conditioner leaking",description:"Water is dripping near the classroom entrance.",category:"HVAC",priority:"Medium",status:"In Progress",location:"Engineering Building, Room 204",department:"HVAC Maintenance",created_at:new Date().toISOString()},
 {id:"demo2",title:"Exposed electrical wire",description:"A wire appears exposed near a hallway wall.",category:"Electrical",priority:"High",status:"Submitted",location:"Library, Floor 1",department:"Electrical Maintenance",created_at:new Date().toISOString()},
 {id:"demo3",title:"Overflowing waste bin",description:"The waste bin needs collection.",category:"Cleaning",priority:"Low",status:"Resolved",location:"Student Center",department:"Cleaning Services",created_at:new Date().toISOString()}
];

// view -> [page title, subtitle, staff section]
const VIEWS = {
 overview: ["Overview", "Facility issues reported across campus and their current status."],
 myreports: ["My reports", "Follow the reports you submitted from this device."],
 tracking: ["Track a report", "Check progress with the tracking code you received."],
 notifications: ["Notifications", "Updates on your reports."],
 system: ["System overview", "Architecture, the eight approved features and AI results."],
 "staff-signin": ["Staff sign in", "Maintenance staff and administrators.", "dashboard"],
 "staff-dashboard": ["Staff dashboard", "Your department's work at a glance.", "dashboard"],
 "staff-assigned": ["Assigned tasks", "Reports assigned to you.", "assigned"],
 "staff-tasks": ["All issues", "Every report routed to your department.", "tasks"],
 "admin-overview": ["Admin overview", "Campus-wide facility conditions.", "overview"],
 "admin-reports": ["All reports", "Search, assign and update any report.", "reports"],
 "admin-analytics": ["Analytics", "Trends, categories, buildings and response performance.", "analytics"],
 "admin-recurring": ["Recurring problems", "Repeated issues by category, building and location.", "recurring"],
 "admin-escalations": ["Escalations", "Response targets, overdue reports and alerts.", "escalations"],
 "admin-team": ["Staff management", "Create accounts and manage access.", "team"],
 account: ["Account", "Your staff account.", "account"],
};
const SECTION_VIEW = {dashboard: "staff-dashboard", assigned: "staff-assigned", tasks: "staff-tasks", overview: "admin-overview", reports: "admin-reports", analytics: "admin-analytics", recurring: "admin-recurring", escalations: "admin-escalations", team: "admin-team", account: "account"};
const FILTERS = [["all", "All"], ["open", "Open"], ["resolved", "Resolved"]];

export default function App() {
     const [isOnline, setIsOnline] = useState(navigator.onLine);
     const [connectionMessage, setConnectionMessage] = useState("");


 useEffect(() => {
  let active = true;
  let wasOnline = navigator.onLine;

  const checkConnection = async () => {
   try {
    const response = await fetch(
     "https://www.google.com/generate_204",
     { method: "GET", mode: "no-cors", cache: "no-store" }
    );

    if (active) {
     setIsOnline(true);
     if (!wasOnline) {
      setConnectionMessage("Internet connection restored.");
     }
     wasOnline = true;
    }
   } catch {
    if (active) {
     setIsOnline(false);
     setConnectionMessage("You are offline. Check your internet connection.");
     wasOnline = false;
    }
   }
  };

  const handleOnline = () => checkConnection();
  const handleOffline = () => checkConnection();

  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);

  checkConnection();
  const interval = setInterval(checkConnection, 10000);

  return () => {
   active = false;
   clearInterval(interval);
   window.removeEventListener("online", handleOnline);
   window.removeEventListener("offline", handleOffline);
  };
 }, []);

 const [issues,setIssues]=useState(demo),[live,setLive]=useState(false),[loading,setLoading]=useState(true);
 const [notice,setNotice]=useState("Demo mode: connect the backend to save reports.");
 const [query,setQuery]=useState(""),[filter,setFilter]=useState("all"),[modal,setModal]=useState(false);
 const [view,setView]=useState("overview"),[mobileNavOpen,setMobileNavOpen]=useState(false),[bellOpen,setBellOpen]=useState(false),[profileOpen,setProfileOpen]=useState(false);
 const [trackCode,setTrackCode]=useState(""),[toast,setToast]=useState("");
 const [mine,setMine]=useState(loadMyReports),[mineLoading,setMineLoading]=useState(false);
 const closeToast=useCallback(()=>setToast(""),[]);
 const bellRef=useRef(null);

 async function update(id,status,token,note){const item=await patchStatus(id,status,token,note);setIssues(old=>old.map(i=>i.id===id?item:i));setToast(`Report #${id} updated to ${status}.`);return item;}
 const session=useStaffSession({issues,onUpdate:update});
 const staffUser=session.user,isAdmin=staffUser?.role==="admin";

 const refresh=useCallback(async()=>{
  try{setIssues(await getIssues());setLive(true);setNotice("Connected: reports are loaded from the database.");}
  catch{setLive(false);setNotice("Backend unavailable. Demo records are shown; submissions will not be saved.");}
  finally{setLoading(false);}
 },[]);
 useEffect(()=>{refresh();},[refresh]);

 const refreshMine=useCallback(async()=>{
  const list=loadMyReports();
  if(!list.length)return;
  setMineLoading(true);
  const settled=await Promise.allSettled(list.map(r=>Promise.resolve().then(()=>getIssueTracking(r.code))));
  const results={};settled.forEach((r,k)=>{if(r.status==="fulfilled"&&r.value)results[list[k].code]=r.value;});
  const merged=mergeTracking(list,results);saveMyReports(merged);setMine(merged);setMineLoading(false);
 },[]);
 useEffect(()=>{if(live)refreshMine();},[live,refreshMine]);
 useEffect(()=>{if(["myreports","notifications"].includes(view)&&live)refreshMine();},[view,live,refreshMine]);
 useEffect(()=>{if(!bellOpen)return undefined;const close=e=>{if(!bellRef.current?.contains(e.target))setBellOpen(false);};document.addEventListener("mousedown",close);return()=>document.removeEventListener("mousedown",close);},[bellOpen]);
 // Leaving a staff page after sign-out goes back to the public overview.
 useEffect(()=>{if(!staffUser&&VIEWS[view]?.[2]&&view!=="staff-signin")setView("staff-signin");if(staffUser&&view==="staff-signin")setView(isAdmin?"admin-overview":"staff-dashboard");},[staffUser,isAdmin,view]);

 const filtered=useMemo(()=>issues
  .filter(i=>filter==="all"||(filter==="open"?isOpen(i):!isOpen(i)))
  .filter(i=>[i.title,i.description,i.category,i.location,i.status,i.department].filter(Boolean).join(" ").toLowerCase().includes(query.toLowerCase())),[issues,query,filter]);
 const open=issues.filter(isOpen).length;
 const processing=issues.filter(i=>i.status==="In Progress").length;
 const resolved=issues.length-open;
 const recent=[...issues].sort((a,b)=>new Date(b.created_at)-new Date(a.created_at)).slice(0,5);
 const unread=unreadUpdates(mine);
 // Signed-in staff see open escalation alerts under the bell; students see updates on their reports.
 const staffAlerts=staffUser?(session.escalations||[]).filter(e=>!e.acknowledged_at):[];
 const bellCount=staffUser?staffAlerts.length:unread.length;

 function saved(item){
  setIssues(old=>[item,...old.filter(i=>typeof i.id==="number")]);setLive(true);
  setNotice("Connected: reports are loaded from the database.");
  setMine(rememberReport(item));
 }
 const go=v=>{setView(v);setMobileNavOpen(false);setBellOpen(false);setProfileOpen(false);};
 const track=code=>{setTrackCode(code);setModal(false);go("tracking");};
 const markRead=()=>{const m=markAllSeen(mine);saveMyReports(m);setMine(m);};
 const navItem=(v,Icon,label,badge)=><button key={v} className={`nav-link ${view===v?"active":""}`} aria-current={view===v?"page":undefined} onClick={()=>go(v)}><Icon size={18} aria-hidden="true"/><span>{label}</span>{badge?<span className="nav-badge">{badge}</span>:null}</button>;
 const [title,sub,section]=VIEWS[view]||VIEWS.overview;
 const staffView=!!section;

 return <div className="app">
  <aside className="sidebar">
   <div className="sidebar-top">
    <div className="brand"><div className="brand-mark"><Activity size={20} aria-hidden="true"/></div><div><strong>INNOVEXA</strong><span>Smart Campus</span></div></div>
    <button className="mobile-menu-toggle" type="button" aria-expanded={mobileNavOpen} aria-controls="mobile-workspace-nav" onClick={()=>setMobileNavOpen(o=>!o)}>{mobileNavOpen?<X size={18}/>:<Menu size={18}/>}<span>Menu</span></button>
   </div>
   <nav className={`nav ${mobileNavOpen?"open":""}`} id="mobile-workspace-nav" aria-label="Workspace navigation">
    <div className="nav-group"><span className="nav-heading">Campus</span>
     {navItem("overview",LayoutDashboard,"Overview")}
     <button className="nav-link" onClick={()=>{setModal(true);setMobileNavOpen(false);}}><Plus size={18} aria-hidden="true"/><span>Report an issue</span></button>
     {navItem("myreports",FileText,"My reports",mine.length||null)}
     {navItem("tracking",Search,"Track a report")}
     {navItem("notifications",Bell,"Notifications",unread.length||null)}
    </div>
    {staffUser?<div className="nav-group"><span className="nav-heading">Maintenance</span>
     {navItem("staff-dashboard",ClipboardList,"Staff dashboard")}
     {navItem("staff-assigned",UserCheck,"Assigned tasks")}
     {navItem("staff-tasks",ListChecks,isAdmin?"Department queue":"All issues")}
    </div>:<div className="nav-group"><span className="nav-heading">Staff</span>{navItem("staff-signin",LogIn,"Staff sign in")}</div>}
    <div className="nav-group"><span className="nav-heading">About</span>{navItem("system",Info,"System overview")}</div>
    {isAdmin&&<div className="nav-group"><span className="nav-heading">Administration</span>
     {navItem("admin-overview",ShieldCheck,"Admin overview")}
     {navItem("admin-reports",Inbox,"All reports")}
     {navItem("admin-analytics",ChartColumn,"Analytics")}
     {navItem("admin-recurring",Repeat,"Recurring problems")}
     {navItem("admin-escalations",Siren,"Escalations")}
     {navItem("admin-team",Users,"Staff management")}
    </div>}
   </nav>
   <div className="sidebar-foot">
    <div className="safety-note"><ShieldAlert size={18} aria-hidden="true"/><p>For immediate danger, contact campus security or emergency services. This system is not an emergency service.</p></div>
    <div className="team-chip"><span className="team-avatar">IX</span><div><b>Team INNOVEXA</b><span>Tongmyong University</span></div></div>
   </div>
  </aside>

  <main className="main">
   <header className="page-head">
    <div className="page-title"><h1>{title}</h1><p>{sub}</p></div>
    <div className="page-actions">
     <span className={`conn-pill ${loading?"checking":live?"connected":""}`}><i aria-hidden="true"/>{loading?"Connecting…":live?"Backend connected":"Demo mode"}</span>
     <div className="popover-anchor" ref={bellRef}>
      <button className="icon-btn bell" aria-label={`Notifications${bellCount?`, ${bellCount} new`:""}`} aria-expanded={bellOpen} onClick={()=>setBellOpen(o=>!o)}><Bell size={19}/>{bellCount>0&&<span className="bell-count">{bellCount}</span>}</button>
      {bellOpen&&<div className="popover" role="dialog" aria-label="Notifications">
       {staffUser?<>
        <div className="popover-head"><strong>Escalation alerts</strong></div>
        {staffAlerts.length?<ul className="alert-list compact">{staffAlerts.slice(0,5).map(e=><li key={e.id}><Siren size={16} aria-hidden="true"/><div><strong>#{e.issue_id} {e.issue_title}</strong><span>{e.reason}</span></div></li>)}</ul>
        :<p className="muted popover-empty">No open escalation alerts.</p>}
        <button className="btn btn-secondary btn-sm btn-block" onClick={()=>{setBellOpen(false);go(isAdmin?"admin-escalations":"staff-dashboard");}}>{isAdmin?"Open escalations":"Open dashboard"}</button>
       </>:<>
        <div className="popover-head"><strong>Notifications</strong>{unread.length>0&&<button className="btn btn-ghost btn-sm" onClick={markRead}>Mark all as read</button>}</div>
        <Notifications compact reports={mine} onTrack={track}/>
        <button className="btn btn-secondary btn-sm btn-block" onClick={()=>go("notifications")}>View all</button>
       </>}
      </div>}
     </div>
     {staffUser?<div className="popover-anchor">
      <button className="profile-chip" aria-expanded={profileOpen} onClick={()=>setProfileOpen(o=>!o)}><span className="avatar" aria-hidden="true">{staffUser.full_name.split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase()}</span><span className="profile-text"><b>{staffUser.full_name}</b><span>{isAdmin?"Administrator":staffUser.department}</span></span></button>
      {profileOpen&&<div className="popover popover-menu" role="menu">
       <button role="menuitem" className="menu-item" onClick={()=>go("account")}><KeyRound size={16}/>Account</button>
       <button role="menuitem" className="menu-item" onClick={()=>{setProfileOpen(false);session.signOut();go("overview");}}><LogOut size={16}/>Sign out</button>
      </div>}
     </div>:!staffView&&<button className="btn btn-ghost btn-sm hide-sm" onClick={()=>go("staff-signin")}><LogIn size={16}/>Staff sign in</button>}
     {!staffView&&<button className="btn btn-primary" onClick={()=>setModal(true)}><Plus size={16}/>Report issue</button>}
    </div>
   </header>

   {connectionMessage&&<div className={`banner ${isOnline?"banner-ok":"banner-error"}`} role={isOnline?"status":"alert"}>{!isOnline&&<WifiOff size={16} aria-hidden="true"/>}{connectionMessage}</div>}
   {!loading&&<div className={`banner ${live?"banner-ok banner-quiet":"banner-warn"}`} role="status">{!live&&<AlertTriangle size={16} aria-hidden="true"/>}{notice}</div>}

   {staffView?<Staff issues={issues} live={live} onUpdate={update} session={session} section={section} onSectionChange={k=>go(SECTION_VIEW[k]||"staff-dashboard")}/>
   :view==="tracking"?<TrackIssue initialCode={trackCode}/>
   :view==="myreports"?<MyReports reports={mine} loading={mineLoading&&!mine.some(r=>r.last_status)} onRefresh={refreshMine} onTrack={track} onReport={()=>setModal(true)}/>
   :view==="notifications"?<Notifications reports={mine} onMarkRead={markRead} onTrack={track}/>
   :view==="system"?<SystemOverview onOpen={v=>{if(v==="report"){setModal(true);return;}const needsStaff=v.startsWith("staff-")||v.startsWith("admin-");go(needsStaff&&!staffUser?"staff-signin":needsStaff&&v.startsWith("admin-")&&!isAdmin?"staff-dashboard":v);}}/>
   :<>
    <section className="welcome">
     <div><h2>Spotted something broken or unsafe?</h2><p>Report it with a photo or a short description. INNOVEXA routes it to the right maintenance team, and you can follow it with a tracking code.</p></div>
     <div className="welcome-actions"><button className="btn btn-secondary" onClick={()=>go("tracking")}><Search size={16}/>Track a report</button><button className="btn btn-secondary" onClick={()=>go("myreports")}><FileText size={16}/>My reports{mine.length?` (${mine.length})`:""}</button></div>
    </section>
    <section className="metrics" aria-label="Report summary">
     <Metric label="Total reports" value={issues.length} note="All visible records"/>
     <Metric label="Open" value={open} note="Awaiting resolution"/>
     <Metric label="Being processed" value={processing} note="Work in progress"/>
     <Metric label="Resolved" value={resolved} note="Resolved or closed"/>
    </section>
    <section className="panel">
     <div className="panel-head"><div><h2>Recent activity</h2><p>The latest reports on campus.</p></div></div>
     {loading?<SkeletonRows rows={3}/>:recent.length===0?<p className="chart-empty">No reports yet.</p>:
     <ul className="item-list">{recent.map(i=><li key={`recent-${i.id}`}><div><strong className="recent-title">{i.title}</strong><span>{i.department||"Being assigned"}</span></div><span className="item-side"><StatusBadge status={i.status}/><span className="cell-sub">{typeof i.id==="number"?timeAgo(i.created_at):"Demo"}</span></span></li>)}</ul>}
    </section>
    <section className="panel">
     <div className="panel-head">
      <div><h2>All campus reports</h2><p>Locations, photos and descriptions are visible to authorised staff only.</p></div>
      <button className="btn btn-secondary btn-sm" onClick={()=>{setLoading(true);refresh();}}><RefreshCw size={14}/>Refresh</button>
     </div>
     <div className="toolbar">
      <div className="search"><Search size={16} aria-hidden="true"/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search by title, category or department" aria-label="Search reports"/></div>
      <div className="segmented" role="group" aria-label="Filter by status">{FILTERS.map(([k,l])=><button key={k} className={filter===k?"active":""} aria-pressed={filter===k} onClick={()=>setFilter(k)}>{l}</button>)}</div>
      <span className="toolbar-count">{filtered.length} {filtered.length===1?"report":"reports"}</span>
     </div>
     {loading?<SkeletonRows rows={5}/>
     :filtered.length===0?(issues.length===0
       ?<EmptyState icon={Inbox} title="No reports yet" action={<button className="btn btn-primary" onClick={()=>setModal(true)}><Plus size={16}/>Create a report</button>}>When someone reports a facility issue, it appears here with its status.</EmptyState>
       :<EmptyState icon={Search} title="No reports match these filters" action={<button className="btn btn-secondary" onClick={()=>{setQuery("");setFilter("all");}}>Clear filters</button>}>Try a different search term or status.</EmptyState>)
     :<div className="table-wrap"><table className="table reports-table">
      <thead><tr><th scope="col">Report</th><th scope="col">Department</th><th scope="col">Priority</th><th scope="col">Status</th><th scope="col">Reported</th></tr></thead>
      <tbody>{filtered.map(i=><tr key={i.id}>
       <td data-label="Report"><div className="cell-title"><h3>{i.title}</h3><CategoryTag category={i.category}/></div></td>
       <td data-label="Department">{i.department||"Being assigned"}</td>
       <td data-label="Priority"><PriorityBadge priority={i.priority}/></td>
       <td data-label="Status"><StatusBadge status={i.status}/></td>
       <td data-label="Reported"><span className="cell-date">{typeof i.id==="number"?formatDate(i.created_at):"Demo record"}</span><span className="cell-sub">{typeof i.id==="number"?timeAgo(i.created_at):""}</span></td>
      </tr>)}</tbody>
     </table></div>}
    </section>
   </>}
   <footer className="footer">INNOVEXA Smart Campus Facility and Issue Management System<span>Tongmyong University capstone prototype</span></footer>
  </main>
  {modal&&<ReportDialog onClose={()=>setModal(false)} onSaved={saved} onTrack={track}/>}
  <Toast message={toast} onClose={closeToast}/>
 </div>;
}
