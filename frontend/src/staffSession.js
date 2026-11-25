import {useCallback, useEffect, useState} from "react";
import {
  acknowledgeEscalation, assignIssue, bootstrapStaffAdmin, changeStaffPassword, createStaffUser, getEscalations, getIssueHistory, getResponseTargets, getResponseTimes, runEscalationCheck, updateResponseTargets,
  getStaffIssues, getStaffSetupStatus, reviewDuplicate, getStaffUsers, loginStaff, resetStaffPassword, setStaffActive,
} from "./api.js";

/**
 * Staff sign-in and protected data. Lives in App so the sidebar can follow the
 * signed-in role; Staff.jsx creates its own when rendered on its own (tests).
 */
export function useStaffSession({issues = [], onUpdate, enabled = true} = {}) {
  const [setupAvailable, setSetupAvailable] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [bootstrapMode, setBootstrapMode] = useState(false);
  const [token, setToken] = useState("");
  const [user, setUser] = useState(null);
  const [staffIssues, setStaffIssues] = useState(issues);
  const [staffUsers, setStaffUsers] = useState([]);
  const [timings, setTimings] = useState(null);
  const [targets, setTargets] = useState([]), [escalations, setEscalations] = useState([]);
  const [history, setHistory] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    Promise.resolve().then(() => getStaffSetupStatus())
      .then(r => { setSetupAvailable(!!r?.setup_available); setBootstrapMode(!!r?.setup_available); })
      .catch(() => setError("Could not check staff account setup."))
      .finally(() => setAuthReady(true));
  }, [enabled]);

  function loadEscalationData(accessToken) {
    Promise.resolve().then(() => getResponseTargets(accessToken)).then(r => setTargets(Array.isArray(r) ? r : [])).catch(() => setTargets([]));
    Promise.resolve().then(() => getEscalations(accessToken)).then(r => setEscalations(Array.isArray(r) ? r : [])).catch(() => setEscalations([]));
  }
  async function acknowledge(id) {
    try {
      const row = await acknowledgeEscalation(id, token);
      setEscalations(old => old.map(e => (e.id === id ? row : e))); setError("");
    } catch (err) { setError(err.message || "Could not acknowledge the escalation."); }
  }
  async function checkNow() {
    try {
      const r = await runEscalationCheck(token);
      setSuccess(r?.created ? `${r.created} new ${r.created === 1 ? "escalation" : "escalations"} raised.` : "Check complete. No new overdue reports to escalate.");
      loadEscalationData(token);
    } catch (err) { setError(err.message || "Could not run the escalation check."); }
  }
  async function saveTargets(list) {
    try {
      setTargets(await updateResponseTargets(list, token));
      setSuccess("Response targets saved."); setError("");
      loadEscalationData(token);
      return true;
    } catch (err) { setError(err.message || "Could not save response targets."); return false; }
  }
  function loadTimings(accessToken) {
    Promise.resolve().then(() => getResponseTimes(accessToken)).then(r => setTimings(r || null)).catch(() => setTimings(null));
  }

  async function loadSession(session) {
    const records = await getStaffIssues(session.access_token);
    const members = session.user.role === "admin" ? await getStaffUsers(session.access_token) : [];
    setToken(session.access_token); setUser(session.user); setStaffIssues(records); setStaffUsers(members); setError("");
    loadEscalationData(session.access_token);
    if (session.user.role === "admin") loadTimings(session.access_token);
  }

  async function signIn({email, password, bootstrapKey, fullName}) {
    setBusy(true); setError(""); setSuccess("");
    try {
      const session = bootstrapMode
        ? await bootstrapStaffAdmin({bootstrap_key: bootstrapKey, email, full_name: fullName, password, department: "Campus Administration"})
        : await loginStaff(email, password);
      await loadSession(session);
      return true;
    } catch (err) { setError(err.message || "Staff sign-in failed."); return false; }
    finally { setBusy(false); }
  }

  const signOut = useCallback((notice = "") => {
    setToken(""); setUser(null); setStaffUsers([]); setStaffIssues(issues); setHistory({}); setTimings(null); setTargets([]); setEscalations([]);
    setSetupAvailable(false); setBootstrapMode(false); setError(""); setSuccess(notice);
  }, [issues]);

  async function refresh() {
    try {
      setStaffIssues(await getStaffIssues(token)); setError("");
      if (user?.role === "admin") loadTimings(token);
      loadEscalationData(token);
    } catch (err) { setError(err.message || "Could not refresh tasks."); }
  }

  async function changeStatus(id, status, note) {
    try {
      const item = await onUpdate(id, status, token, note);
      setStaffIssues(old => old.map(x => (x.id === id ? item : x)));
      setHistory(old => ({...old, [id]: undefined}));
      setError(""); // the app shows a toast for status changes, so no second banner here
      return true;
    } catch (err) { setError(err.message || "Could not update report."); return false; }
  }

  async function reviewDuplicateOf(id, decision, duplicateOf) {
    try {
      const item = await reviewDuplicate(id, decision, duplicateOf, token);
      setStaffIssues(old => old.map(x => (x.id === id ? item : x)));
      setSuccess(decision === "duplicate" ? `Report #${id} marked as a duplicate of #${duplicateOf}.` : `Report #${id} marked as not a duplicate.`);
      setError("");
    } catch (err) { setError(err.message || "Could not save the duplicate review."); }
  }
  async function assign(id, value) {
    try {
      const item = await assignIssue(id, value ? Number(value) : null, token);
      setStaffIssues(old => old.map(x => (x.id === id ? item : x)));
      setSuccess("Task assignment saved.");
    } catch (err) { setError(err.message || "Could not assign task."); }
  }

  async function loadHistory(id) {
    if (history[id]) return;
    try { const rows = await getIssueHistory(id, token); setHistory(old => ({...old, [id]: rows})); }
    catch (err) { setError(err.message || "Could not load history."); }
  }

  async function addStaff(account) {
    setBusy(true); setError(""); setSuccess("");
    try { await createStaffUser(account, token); setStaffUsers(await getStaffUsers(token)); setSuccess("Staff account created."); return true; }
    catch (err) { setError(err.message || "Could not create account."); return false; }
    finally { setBusy(false); }
  }

  async function updateAccountActive(member) {
    try {
      await setStaffActive(member.id, !member.is_active, token); setStaffUsers(await getStaffUsers(token));
      setSuccess(`Account ${member.is_active ? "deactivated" : "activated"}.`); setError("");
    } catch (err) { setError(err.message || "Could not update account."); }
  }

  async function resetPassword(member, value) {
    if (value.length < 12) { setError("Password must be at least 12 characters."); return false; }
    try {
      await resetStaffPassword(member.id, value, token);
      if (member.id === user.id) { signOut("Your password was reset. Please sign in again."); return true; }
      setSuccess(`Password reset for ${member.full_name}.`); setError(""); return true;
    } catch (err) { setError(err.message || "Could not reset password."); return false; }
  }

  async function updateOwnPassword(current, next) {
    setBusy(true); setError(""); setSuccess("");
    try { await changeStaffPassword(current, next, token); signOut("Your password was changed. Please sign in again."); return true; }
    catch (err) { setError(err.message || "Could not change password."); return false; }
    finally { setBusy(false); }
  }

  return {
    setupAvailable, authReady, bootstrapMode, setBootstrapMode, token, user, staffIssues, staffUsers, timings, history, targets, escalations, acknowledge, checkNow, saveTargets,
    error, setError, success, setSuccess, busy,
    signIn, signOut, refresh, changeStatus, assign, reviewDuplicateOf, loadHistory, addStaff, updateAccountActive, resetPassword, updateOwnPassword,
  };
}
