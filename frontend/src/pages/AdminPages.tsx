import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Status } from "../components/ui";
import { systemApi, wellApi } from "../services/api";
import type { User, Well } from "../types";

export function UsersAdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function load() { setUsers((await systemApi.users()).data); }
  useEffect(() => { load().catch((e) => setError(e.message)); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    try { await systemApi.createUser(data); setMessage("User created."); event.currentTarget.reset(); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Users</h1>
      {error && <Status state="error" message={error} />}
      {message && <p className="text-sm text-ok">{message}</p>}
      <form className="panel p-3 grid md:grid-cols-3 gap-2" onSubmit={submit}>
        <input className="field" name="username" placeholder="Username" required />
        <input className="field" name="email" type="email" placeholder="Email" required />
        <input className="field" name="full_name" placeholder="Full name" required />
        <input className="field" name="password" type="password" placeholder="Password" required />
        <select className="field" name="role" defaultValue="VIEWER"><option>VIEWER</option><option>DRILLING_ENGINEER</option><option>ADMIN</option></select>
        <button className="btn btn-primary">Create user</button>
      </form>
      <div className="space-y-2">{users.map((user) => (
        <article key={user.id} className="panel p-3 text-sm flex flex-wrap gap-3 items-center">
          <span className="tech">{user.username}</span><span>{user.full_name}</span><span>{user.email}</span>
          <select aria-label={`Role ${user.username}`} className="field max-w-[200px]" value={user.role} onChange={async (e) => { await systemApi.updateUser(user.id, { role: e.target.value }); await load(); }}>
            <option>VIEWER</option><option>DRILLING_ENGINEER</option><option>ADMIN</option>
          </select>
          <button className="btn" onClick={async () => { await systemApi.updateUser(user.id, { is_active: !user.is_active }); await load(); }}>{user.is_active ? "Deactivate" : "Activate"}</button>
          <button className="btn text-red-400 hover:bg-red-500/20 border-red-500/30" onClick={async () => { if (window.confirm(`Delete user ${user.username}?`)) { await systemApi.deleteUser(user.id); await load(); } }}>Delete</button>
        </article>
      ))}</div>
    </div>
  );
}

export function AdminWellsPage() {
  const [wells, setWells] = useState<Well[]>([]);
  useEffect(() => { wellApi.list({ page_size: 100, include_archived: true }).then((r) => setWells(r.data.items)); }, []);
  return (
    <div className="space-y-2">
      <h1 className="text-xl font-semibold">Well administration</h1>
      {wells.map((well) => <div key={well.id} className="panel p-2 text-sm flex justify-between"><Link to={`/wells/${well.id}`}>{well.well_id} · {well.well_name}</Link><span>{well.is_archived ? "Archived" : well.status}</span></div>)}
    </div>
  );
}

export function ThresholdPage() {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { systemApi.thresholds().then((r) => setRows(r.data)).catch((e) => setError(e.message)); }, []);
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Risk thresholds</h1>
      <p className="text-sm text-muted">0–low is LOW, through moderate, high, then CRITICAL above the high maximum. Defaults are 29 / 59 / 79.</p>
      {error && <Status state="error" message={error} />}
      {message && <p className="text-sm text-ok">{message}</p>}
      {rows.map((row) => (
        <form key={String(row.category)} className="panel p-3 grid md:grid-cols-4 gap-2 text-sm" onSubmit={async (e) => {
          e.preventDefault();
          const data = Object.fromEntries(new FormData(e.currentTarget).entries());
          const body = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Number(v)]));
          try { await systemApi.updateThreshold(String(row.category), body); setMessage(`${row.category} updated and audited.`); }
          catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
        }}>
          <strong className="md:col-span-4">{String(row.category)}</strong>
          {(["low_max", "moderate_max", "high_max", "alert_min_score", "cooldown_minutes", "torque_rise_pct", "pressure_rise_pct", "flow_change_pct"] as const).map((key) => (
            <label key={key}>{key}<input className="field" name={key} defaultValue={String(row[key])} /></label>
          ))}
          <button className="btn">Save</button>
        </form>
      ))}
    </div>
  );
}

export function AuditPage() {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  useEffect(() => { systemApi.audit().then((r) => setRows(r.data.items)).catch((e) => setError(e.message)); }, []);
  if (error) return <Status state="error" message={error} />;
  return (
    <div className="space-y-2">
      <h1 className="text-xl font-semibold">Audit logs</h1>
      <div className="overflow-x-auto panel"><table className="w-full text-sm"><thead className="text-muted text-left"><tr><th className="p-2">Time</th><th>User</th><th>Action</th><th>Resource</th><th>IP</th></tr></thead><tbody>{rows.map((row) => <tr key={String(row.id)} className="border-t border-line"><td className="p-2 tech">{String(row.timestamp)}</td><td>{String(row.username || "")}</td><td>{String(row.action)}</td><td>{String(row.resource)} {String(row.resource_id || "")}</td><td className="tech">{String(row.ip_address || "")}</td></tr>)}</tbody></table></div>
    </div>
  );
}

export function SystemAdminPage() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [uploads, setUploads] = useState<Array<Record<string, unknown>>>([]);
  const [weights, setWeights] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    Promise.all([systemApi.system(), systemApi.uploads(), systemApi.weights()]).then(([s, u, w]) => {
      setInfo(s.data); setUploads(u.data); setWeights(w.data);
    }).catch((e) => setError(e.message));
  }, []);
  if (error) return <Status state="error" message={error} />;
  if (!info || !weights) return <Status state="loading" />;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">System</h1>
      <section className="panel p-3 text-sm grid md:grid-cols-2 gap-2">
        {Object.entries(info).map(([key, value]) => <div key={key}><span className="text-muted">{key}</span><div className="tech break-all">{typeof value === "object" ? JSON.stringify(value) : String(value)}</div></div>)}
      </section>
      <form className="panel p-3 grid md:grid-cols-3 gap-2" onSubmit={async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.currentTarget).entries());
        const body = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Number(v)]));
        try { await systemApi.updateWeights(body); setMessage("Weights updated."); } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
      }}>
        <h2 className="md:col-span-3 font-medium">Similarity weights (must sum to 1)</h2>
        {Object.entries(weights).map(([key, value]) => <label key={key} className="text-sm">{key}<input className="field" name={key} defaultValue={value} /></label>)}
        <button className="btn">Save weights</button>
      </form>
      {message && <p className="text-sm text-ok">{message}</p>}
      <section>
        <h2 className="font-medium mb-2">Upload management</h2>
        {uploads.filter((u) => u.status === "FAILED").length === 0 && <p className="text-sm text-muted">No processing failures.</p>}
        {uploads.map((u) => <div key={String(u.id)} className="text-sm border-t border-line py-1">{String(u.title)} · {String(u.status)} {u.error_message ? `· ${String(u.error_message)}` : ""}</div>)}
      </section>
    </div>
  );
}
