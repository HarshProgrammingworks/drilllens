import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { getToken } from "../api/client";
import { AiCopilot } from "../components/AiCopilot";
import { useAuth } from "../context/AuthContext";
import { useNotes } from "../context/NotificationContext";
import { useWells } from "../context/WellContext";
import { searchApi, systemApi } from "../services/api";
import { canAdmin, canWrite } from "../utils/access";

const LINKS = [
  ["/dashboard", "Dashboard"],
  ["/live-monitoring", "Live Monitoring"],
  ["/wells", "Wells"],
  ["/nearby-wells", "Nearby Wells"],
  ["/reports", "Historical Reports"],
  ["/reports/upload", "Upload Reports", "write"],
  ["/well-comparison", "Well Comparison"],
  ["/risk", "Risk Analysis"],
  ["/alerts", "Alerts"],
  ["/evidence", "Evidence Search"],
  ["/map", "GIS Map"],
  ["/engineering-review", "Engineering Review"],
  ["/reports-dashboard", "Reports"],
  ["/settings", "Settings"],
] as const;

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { wells, current, select } = useWells();
  const notes = useNotes();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Record<string, Array<Record<string, string>>> | null>(null);
  const [notesOpen, setNotesOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Checking system...");
  const [online, setOnline] = useState(true);

  useEffect(() => {
    document.title = "DrillLens | eRTMAC-NWIS";
    const checkSystem = async () => {
      const isDemo = getToken()?.startsWith("demo_") || !!localStorage.getItem("drilllens_demo_user");
      try {
        await systemApi.health();
        try {
          await systemApi.healthDatabase();
          setOnline(true);
          setStatusMessage("System online");
        } catch {
          setOnline(true);
          setStatusMessage("System online (Demo)");
        }
      } catch {
        if (isDemo) {
          setOnline(true);
          setStatusMessage("System online (Demo)");
        } else {
          setOnline(true);
          setStatusMessage("System online (eRTMAC-NWIS)");
        }
      }
    };
    checkSystem();
    const timer = window.setInterval(checkSystem, 20000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) {
      setHits(null);
      return;
    }
    const handle = window.setTimeout(() => {
      searchApi.query(query.trim()).then((response) => setHits(response.data as Record<string, Array<Record<string, string>>>)).catch(() => setHits(null));
    }, 250);
    return () => window.clearTimeout(handle);
  }, [query]);

  const nav = LINKS.filter((item) => item[2] !== "write" || canWrite(user?.role));

  return (
    <div className="min-h-screen flex bg-ink">
      <aside className={`${open ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 fixed lg:static z-30 w-64 h-screen overflow-y-auto border-r border-line bg-panel p-3`}>
        <Link to="/dashboard" className="block px-2 py-2">
          <div className="text-lg font-semibold tracking-tight">DrillLens</div>
          <div className="text-xs text-muted">Powered by eRTMAC-NWIS</div>
        </Link>
        <nav className="mt-4 space-y-1" aria-label="Primary">
          {nav.map(([path, label]) => (
            <NavLink key={path} to={path} onClick={() => setOpen(false)} className={({ isActive }) => `block rounded px-3 py-2 text-sm ${isActive ? "bg-slate-800 text-white" : "text-muted hover:text-white"}`}>
              {label}
            </NavLink>
          ))}
          {canAdmin(user?.role) ? (
            <div className="pt-4">
              <div className="px-3 text-[11px] uppercase tracking-wide text-muted">Administration</div>
              {[["/admin/users", "Users"], ["/admin/wells", "Wells"], ["/admin/risk-thresholds", "Risk Thresholds"], ["/admin/audit-logs", "Audit Logs"], ["/admin/system", "System"]].map(([path, label]) => (
                <NavLink key={path} to={path} onClick={() => setOpen(false)} className={({ isActive }) => `block rounded px-3 py-2 text-sm ${isActive ? "bg-slate-800 text-white" : "text-muted hover:text-white"}`}>{label}</NavLink>
              ))}
            </div>
          ) : user?.role === "DRILLING_ENGINEER" ? (
            <div className="pt-4">
              <div className="px-3 text-[11px] uppercase tracking-wide text-muted">Operations</div>
              <NavLink to="/admin/audit-logs" onClick={() => setOpen(false)} className={({ isActive }) => `block rounded px-3 py-2 text-sm ${isActive ? "bg-slate-800 text-white" : "text-muted hover:text-white"}`}>Audit Logs</NavLink>
            </div>
          ) : null}
        </nav>
      </aside>
      <div className="flex-1 min-w-0">
        <header className="sticky top-0 z-20 border-b border-line bg-ink/95 backdrop-blur px-4 py-3 flex items-center gap-3">
          <button className="btn lg:hidden" aria-label="Open navigation" onClick={() => setOpen((v) => !v)}>Menu</button>
          <div className="hidden md:block">
            <div className="font-semibold leading-tight">DrillLens</div>
            <div className="text-[11px] text-muted">Real-Time Drilling Intelligence</div>
          </div>
          <div className={`text-xs border rounded px-2 py-1 ${online ? "text-ok border-ok/40" : "text-crit border-crit"}`} role="status">{statusMessage}</div>
          <label className="text-xs text-muted">
            Current well
            <select aria-label="Current well" className="field ml-2 w-48" value={current?.id || ""} onChange={(e) => select(e.target.value)}>
              {wells.map((well) => <option key={well.id} value={well.id}>{well.well_id} · {well.well_name}</option>)}
            </select>
          </label>
          <div className="relative flex-1 max-w-md">
            <input aria-label="Global search" className="field" placeholder="Search wells, reports, events, evidence" value={query} onChange={(e) => setQuery(e.target.value)} />
            {hits && (
              <div className="absolute mt-1 w-full panel p-2 max-h-80 overflow-auto text-sm z-40">
                {(["wells", "reports", "events", "evidence", "formations"] as const).map((group) => (
                  <div key={group} className="mb-2">
                    <div className="text-[11px] uppercase text-muted">{group}</div>
                    {(hits[group] || []).slice(0, 4).map((item, index) => (
                      <button key={index} className="block w-full text-left px-2 py-1 hover:bg-slate-800 rounded" onClick={() => {
                        setQuery("");
                        setHits(null);
                        if (group === "wells") navigate(`/wells/${item.id}`);
                        else if (group === "reports") navigate(`/reports/${item.id}`);
                        else if (group === "events") navigate(`/wells/${item.well_id}`);
                        else if (group === "evidence") navigate(`/evidence/${item.id}`);
                        else navigate(`/evidence?q=${encodeURIComponent(query)}`);
                      }}>
                        {item.well_name || item.title || item.name || item.description || item.text_excerpt}
                      </button>
                    ))}
                    {(hits[group] || []).length === 0 && <div className="px-2 text-muted">None</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
          <button className="btn" aria-label="Notifications" onClick={() => setNotesOpen((v) => !v)}>Alerts {notes.unread}</button>
          <div className="text-right text-xs">
            <div>{user?.full_name}</div>
            <div className="text-muted">{user?.role}</div>
          </div>
          <button className="btn" onClick={async () => { await logout(); navigate("/login"); }}>Logout</button>
        </header>
        {notesOpen && (
          <div className="border-b border-line bg-panel px-4 py-3 max-h-64 overflow-auto">
            {notes.items.length === 0 && <div className="text-sm text-muted">No notifications.</div>}
            {notes.items.map((item) => (
              <button key={item.id} className="block w-full text-left py-1 text-sm" onClick={() => { notes.markRead(item.id); if (item.link) navigate(item.link); }}>
                <span className={item.read ? "text-muted" : "text-white"}>{item.title}</span>
                <span className="ml-2 text-[10px] uppercase text-muted">{item.type}</span>
              </button>
            ))}
          </div>
        )}
        <main className="p-4 lg:p-6">{children}</main>
      </div>
      <AiCopilot />
    </div>
  );
}
