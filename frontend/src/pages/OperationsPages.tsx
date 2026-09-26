import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ParameterChart } from "../charts/ParameterChart";
import { PARAMS, Provenance, RiskBadge, Status, Tech } from "../components/ui";
import { useMonitoring } from "../context/MonitoringContext";
import { useWells } from "../context/WellContext";
import { useAuth } from "../context/AuthContext";
import { WellMap, type MapWell } from "../maps/WellMap";
import { riskApi, systemApi, wellApi } from "../services/api";
import type { RiskCard, Well } from "../types";
import { canAdmin, canWrite } from "../utils/access";

const FLOW = ["Current well", "Live parameters", "Nearby wells", "Historical events", "Similarity", "Risk", "Evidence", "Review"];

export function DashboardPage() {
  const { current } = useWells();
  const { live, history } = useMonitoring();
  const [risks, setRisks] = useState<RiskCard[]>([]);
  const [latest, setLatest] = useState<Record<string, { value: number; unit: string }> | null>(null);
  const [meta, setMeta] = useState<{ timestamp?: string; source?: string; provenance?: string }>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!current) return;
    setLoading(true);
    Promise.all([riskApi.current(current.id), wellApi.latest(current.id)])
      .then(([risk, params]) => {
        setRisks(risk.data || []);
        setLatest(params.data?.parameters || null);
        setMeta({ timestamp: params.data?.timestamp, source: params.data?.source, provenance: params.data?.provenance });
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [current?.id, live?.timestamp]);

  if (!current) return <Status state={loading ? "loading" : "empty"} message="No well is available." />;
  const values = live?.parameters;
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold">DrillLens</h1>
        <p className="text-sm text-muted">Real-Time Drilling Intelligence · Powered by eRTMAC-NWIS</p>
      </header>
      <ol className="flex flex-wrap gap-2 text-xs text-muted">{FLOW.map((step) => <li key={step} className="border border-line rounded px-2 py-1">{step}</li>)}</ol>
      <section className="panel p-4 grid md:grid-cols-4 gap-3 text-sm">
        <div><div className="text-muted">Well name</div><div>{current.well_name}</div></div>
        <div><div className="text-muted">Well ID</div><div className="tech">{current.well_id}</div></div>
        <div><div className="text-muted">Field</div><div>{current.field}</div></div>
        <div><div className="text-muted">Current depth</div><div className="tech">{values?.depth ?? current.current_depth ?? "—"} m</div></div>
        <div><div className="text-muted">Formation</div><div>{current.formation || "—"}</div></div>
        <div><div className="text-muted">Drilling status</div><div>{current.status}</div></div>
        <div><div className="text-muted">Current operation</div><div>{current.current_operation || "—"}</div></div>
        <div><div className="text-muted">Last update</div><div className="tech">{live?.timestamp || current.updated_at || "—"}</div></div>
      </section>
      {error && <Status state="error" message={error} />}
      {loading && <Status state="loading" />}
      <section className="grid md:grid-cols-5 gap-3">
        {PARAMS.map((param) => {
          const liveValue = values?.[param.key];
          const stored = latest?.[param.key];
          const value = liveValue ?? stored?.value;
          return (
            <article key={param.key} className="panel p-3">
              <div className="text-xs text-muted">{param.label}</div>
              <div className="tech text-lg">{value ?? "—"} <span className="text-xs text-muted">{param.unit}</span></div>
              <div className="text-[11px] text-muted tech">{live?.timestamp || meta.timestamp || "—"}</div>
              <Provenance value={live ? "SIMULATED" : meta.provenance} />
            </article>
          );
        })}
      </section>
      <section className="grid md:grid-cols-3 gap-3">
        {risks.map((risk) => (
          <article key={risk.category} className="panel p-3 space-y-1">
            <div className="flex justify-between"><h2 className="text-sm font-medium">{risk.label}</h2><RiskBadge level={risk.level} /></div>
            <div className="tech text-2xl">{risk.score}</div>
            <div className="text-xs text-muted">Confidence {risk.confidence} · analytical, not a probability of occurrence</div>
            <p className="text-sm">{risk.reasons?.[0]}</p>
            <div className="text-xs text-muted">Evidence {risk.evidence_count} · <span className="tech">{risk.timestamp}</span></div>
            <Provenance value={risk.provenance || "RULE-BASED"} />
            {risk.evidence?.[0] && <Link className="text-sm text-info" to={`/evidence/${risk.evidence[0].id}`}>View evidence</Link>}
          </article>
        ))}
        {!loading && risks.length === 0 && <Status state="empty" message="No risk analysis is stored yet. Open Risk Analysis to calculate indicators." />}
      </section>
      <ParameterChart title="Depth and torque versus time" rows={history} xKey="timestamp" series={[{ key: "depth", label: "Depth (m)" }, { key: "torque", label: "Torque" }]} />
      <p className="text-xs text-muted">Decision support only. Final operational decisions remain with qualified drilling engineers.</p>
    </div>
  );
}

export function LivePage() {
  const { current } = useWells();
  const { user } = useAuth();
  const { live, history, connected, error } = useMonitoring();
  const [message, setMessage] = useState("");
  if (!current) return <Status state="empty" message="Select a well." />;
  return (
    <div className="space-y-4">
      <header className="flex flex-wrap justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Live monitoring</h1>
          <p className="text-sm text-muted">{current.well_id} · socket {connected ? "connected" : "not streaming"}</p>
        </div>
        {current.simulate_sensors && <div className="border border-warn text-warn text-xs rounded px-2 py-1">DEMO SENSOR STREAM</div>}
      </header>
      {error && <Status state="error" message={error} />}
      {!current.simulate_sensors && <Status state="empty" message="This well has no sensor adapter enabled. Historical samples remain available below." />}
      <div className="grid md:grid-cols-5 gap-3">
        {PARAMS.map((param) => (
          <article key={param.key} className="panel p-3">
            <div className="text-xs text-muted">{param.label}</div>
            <div className="tech text-xl">{live?.parameters?.[param.key] ?? "—"} <span className="text-xs">{param.unit}</span></div>
            <div className="text-[11px] text-muted">Current <Provenance value={live?.source || "HISTORICAL"} /></div>
          </article>
        ))}
      </div>
      {canWrite(user?.role) && current.simulate_sensors && (
        <div className="panel p-3 flex flex-wrap gap-2 items-center">
          <span className="text-sm">Trigger a labeled demo condition</span>
          {["normal", "stuck_pipe", "kick", "lost_circulation", "mud", "torque", "cementing"].map((scenario) => (
            <button key={scenario} className="btn" onClick={async () => {
              await systemApi.scenario(current.well_id, scenario);
              setMessage(`DEMO scenario ${scenario} applied. Risk analysis runs on the simulator interval.`);
            }}>{scenario}</button>
          ))}
          {message && <p className="text-xs text-muted w-full">{message}</p>}
        </div>
      )}
      <div className="grid xl:grid-cols-2 gap-3">
        <ParameterChart title="Depth vs time" rows={history} xKey="timestamp" series={[{ key: "depth", label: "Depth (m)" }]} />
        <ParameterChart title="ROP vs time" rows={history} xKey="timestamp" series={[{ key: "rop", label: "ROP (m/h)" }]} />
        <ParameterChart title="Torque vs depth" rows={history} xKey="depth" series={[{ key: "torque", label: "Torque" }]} />
        <ParameterChart title="WOB vs depth" rows={history} xKey="depth" series={[{ key: "wob", label: "WOB" }]} />
        <ParameterChart title="Pressure vs depth" rows={history} xKey="depth" series={[{ key: "standpipe_pressure", label: "Standpipe" }, { key: "pump_pressure", label: "Pump" }]} />
        <ParameterChart title="Mud weight vs depth" rows={history} xKey="depth" series={[{ key: "mud_weight", label: "Mud weight" }]} />
      </div>
      <p className="text-xs text-muted">LIVE values on a simulated well are marked SIMULATED. HISTORICAL samples keep their stored provenance. Replace SENSOR_ADAPTER to connect a rig feed.</p>
    </div>
  );
}

export function WellsPage() {
  const { user } = useAuth();
  const { reload } = useWells();
  const [items, setItems] = useState<Well[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("well_name");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(false);

  async function load(next = page) {
    setLoading(true);
    try {
      const response = await wellApi.list({ q, status: status || undefined, sort, page: next, page_size: 10, include_archived: false });
      setItems(response.data.items);
      setTotal(response.data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(1); }, [q, status, sort]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between"><h1 className="text-xl font-semibold">Wells</h1>{canWrite(user?.role) && <button className="btn btn-primary" onClick={() => setForm((v) => !v)}>Create well</button>}</div>
      <div className="flex gap-2 flex-wrap">
        <input aria-label="Search wells" className="field max-w-xs" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label="Filter status" className="field max-w-[180px]" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {["PLANNED", "DRILLING", "SUSPENDED", "COMPLETED", "ABANDONED"].map((item) => <option key={item}>{item}</option>)}
        </select>
        <select aria-label="Sort wells" className="field max-w-[180px]" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="well_name">Name</option>
          <option value="well_id">Well ID</option>
          <option value="current_depth">Depth</option>
          <option value="field">Field</option>
        </select>
      </div>
      {form && <WellForm onDone={() => { setForm(false); load(); reload(); }} />}
      {error && <Status state="error" message={error} />}
      {loading ? <Status state="loading" /> : items.length === 0 ? <Status state="empty" message="No wells match these filters." /> : (
        <div className="overflow-x-auto panel">
          <table className="w-full text-sm">
            <thead className="text-left text-muted"><tr><th className="p-2">Well ID</th><th>Name</th><th>Field</th><th>Status</th><th>Depth</th><th>Formation</th><th></th></tr></thead>
            <tbody>
              {items.map((well) => (
                <tr key={well.id} className="border-t border-line">
                  <td className="p-2 tech">{well.well_id}</td>
                  <td>{well.well_name}</td>
                  <td>{well.field}</td>
                  <td>{well.status}</td>
                  <td className="tech">{well.current_depth}</td>
                  <td>{well.formation}</td>
                  <td><Link className="text-info" to={`/wells/${well.id}`}>View</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex gap-2 text-sm"><button className="btn" disabled={page <= 1} onClick={() => { setPage(page - 1); load(page - 1); }}>Previous</button><span className="text-muted">{total} wells</span><button className="btn" onClick={() => { setPage(page + 1); load(page + 1); }}>Next</button></div>
    </div>
  );
}

function WellForm({ onDone, initial }: { onDone: () => void; initial?: Well }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const body: Record<string, unknown> = Object.fromEntries(data.entries());
    body.latitude = Number(body.latitude);
    body.longitude = Number(body.longitude);
    body.current_depth = body.current_depth ? Number(body.current_depth) : null;
    body.simulate_sensors = data.get("simulate_sensors") === "on";
    try {
      if (initial) await wellApi.update(initial.id, body);
      else await wellApi.create(body);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }
  const well = initial;
  return (
    <form className="panel p-4 grid md:grid-cols-3 gap-3" onSubmit={submit}>
      {!well && <input className="field" name="well_id" placeholder="Well ID" required />}
      <input className="field" name="well_name" placeholder="Name" defaultValue={well?.well_name} required />
      <input className="field" name="field" placeholder="Field" defaultValue={well?.field} required />
      <input className="field" name="operator" placeholder="Operator" defaultValue={well?.operator} required />
      <input className="field" name="latitude" placeholder="Latitude" defaultValue={well?.latitude ?? ""} required />
      <input className="field" name="longitude" placeholder="Longitude" defaultValue={well?.longitude ?? ""} required />
      <input className="field" name="formation" placeholder="Formation" defaultValue={well?.formation ?? ""} />
      <input className="field" name="current_depth" placeholder="Depth (m)" defaultValue={well?.current_depth ?? ""} />
      <select className="field" name="status" defaultValue={well?.status || "PLANNED"}>{["PLANNED", "DRILLING", "SUSPENDED", "COMPLETED", "ABANDONED"].map((item) => <option key={item}>{item}</option>)}</select>
      <input className="field" name="well_type" placeholder="Well type" defaultValue={well?.well_type || "DEVELOPMENT"} />
      <input className="field" name="trajectory_type" placeholder="Trajectory" defaultValue={well?.trajectory_type || "VERTICAL"} />
      <input className="field" name="current_operation" placeholder="Operation" defaultValue={well?.current_operation || ""} />
      <label className="text-sm flex items-center gap-2"><input type="checkbox" name="simulate_sensors" defaultChecked={well?.simulate_sensors} /> Demo sensor stream</label>
      {error && <p className="text-crit text-sm md:col-span-3">{error}</p>}
      <button className="btn btn-primary">Save</button>
    </form>
  );
}

export function WellDetailPage() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const [well, setWell] = useState<Well | null>(null);
  const [tab, setTab] = useState("Overview");
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [trajectory, setTrajectory] = useState<Array<Record<string, number>>>([]);
  const [params, setParams] = useState<Array<Record<string, number | string>>>([]);
  const [similar, setSimilar] = useState<Array<Record<string, unknown>>>([]);
  const [reviews, setReviews] = useState<Array<Record<string, unknown>>>([]);
  const [risks, setRisks] = useState<RiskCard[]>([]);
  const [tile, setTile] = useState("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    setError("");
    wellApi.get(id).then((r) => setWell(r.data)).catch((e) => setError(e.message));
    wellApi.events(id).then((r) => setEvents(r.data)).catch(() => undefined);
    wellApi.trajectory(id).then((r) => setTrajectory(r.data)).catch(() => undefined);
    wellApi.parameters(id).then((r) => setParams(r.data as unknown as Array<Record<string, number | string>>)).catch(() => undefined);
    wellApi.similar(id).then((r) => setSimilar(r.data)).catch(() => undefined);
    wellApi.reviews(id).then((r) => setReviews(r.data)).catch(() => undefined);
    riskApi.history(id).then((r) => setRisks(r.data as unknown as RiskCard[])).catch(() => undefined);
    systemApi.config().then((r) => setTile(r.data.osm_tile_url)).catch(() => undefined);
  }, [id]);

  if (error) return <Status state="error" message={error} />;
  if (!well) return <Status state="loading" />;
  const markers: MapWell[] = well.latitude != null && well.longitude != null ? [{ id: well.id, well_id: well.well_id, well_name: well.well_name, latitude: well.latitude, longitude: well.longitude, depth: well.current_depth, formation: well.formation, status: well.status, kind: "current" }] : [];
  return (
    <div className="space-y-4">
      <div className="flex justify-between gap-3"><div><h1 className="text-xl font-semibold">{well.well_name}</h1><p className="tech text-sm text-muted">{well.well_id} · {well.source_type}</p></div>{canWrite(user?.role) && <button className="btn" onClick={() => setEditing((v) => !v)}>Edit</button>}</div>
      {editing && <WellForm initial={well} onDone={() => { setEditing(false); wellApi.get(id).then((r) => setWell(r.data)); }} />}
      <div className="flex flex-wrap gap-2">{["Overview", "Map", "Trajectory", "Parameters", "Historical Events", "Risk History", "Similarity", "Engineering Reviews"].map((item) => <button key={item} className={`btn ${tab === item ? "btn-primary" : ""}`} onClick={() => setTab(item)}>{item}</button>)}</div>
      {tab === "Overview" && <section className="panel p-4 grid md:grid-cols-3 gap-2 text-sm"><div>Field {well.field}</div><div>Operator {well.operator}</div><div>Status {well.status}</div><div>Depth <Tech>{well.current_depth}</Tech> m</div><div>Formation {well.formation}</div><div>Operation {well.current_operation}</div><div>Type {well.well_type}</div><div>Trajectory {well.trajectory_type}</div><Provenance value={well.source_type} /></section>}
      {tab === "Map" && <WellMap wells={markers} tileUrl={tile} trajectories={[{ id: well.id, positions: trajectory.map((s) => [s.latitude, s.longitude] as [number, number]) }]} />}
      {tab === "Trajectory" && <div className="overflow-x-auto panel"><table className="w-full text-sm"><tbody>{trajectory.map((s) => <tr key={s.station_index} className="border-t border-line"><td className="p-2 tech">{s.measured_depth} m</td><td>Inc {s.inclination}</td><td className="tech">{s.latitude}, {s.longitude}</td></tr>)}</tbody></table></div>}
      {tab === "Parameters" && <ParameterChart title="Torque and ROP" rows={params} xKey="timestamp" series={[{ key: "torque", label: "Torque" }, { key: "rop", label: "ROP" }]} />}
      {tab === "Historical Events" && <EventTable rows={events} />}
      {tab === "Risk History" && <div className="space-y-2">{risks.slice(0, 30).map((risk, index) => <div key={index} className="panel p-2 text-sm flex gap-3"><RiskBadge level={String(risk.level)} /><span>{String(risk.category)}</span><span className="tech">{String(risk.score)}</span><Provenance value="RULE-BASED" /></div>)}{risks.length === 0 && <Status state="empty" message="No stored risk history." />}</div>}
      {tab === "Similarity" && <SimilarityTable rows={similar} />}
      {tab === "Engineering Reviews" && <ReviewList rows={reviews} />}
      {canAdmin(user?.role) && <button className="btn" onClick={async () => { await wellApi.archive(well.id); setWell({ ...well, is_archived: true }); }}>Archive well</button>}
    </div>
  );
}

export function EventTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) return <Status state="empty" message="No historical events are stored." />;
  return <div className="overflow-x-auto panel"><table className="w-full text-sm"><thead className="text-muted text-left"><tr><th className="p-2">Depth</th><th>Type</th><th>Formation</th><th>Description</th><th>Source</th></tr></thead><tbody>{rows.map((row) => <tr key={String(row.id)} className="border-t border-line align-top"><td className="p-2 tech">{String(row.depth_start ?? "")}</td><td>{String(row.event_type)}</td><td>{String(row.formation || "")}</td><td>{String(row.description)}</td><td><Provenance value={String(row.source_type || "")} /></td></tr>)}</tbody></table></div>;
}

export function SimilarityTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) return <Status state="empty" message="No similarity results." />;
  return <div className="space-y-2">{rows.map((row) => <article key={String(row.well_id)} className="panel p-3 text-sm"><div className="flex justify-between"><Link to={`/wells/${row.well_id}`} className="font-medium">{String(row.well_name)} <span className="tech">{String(row.well_code)}</span></Link><span className="tech">{Number(row.overall_score).toFixed(2)}</span></div><p className="text-muted mt-1">{String(row.explanation)}</p><div className="text-xs mt-1 tech">Geo {String(row.geographic_score)} · Formation {String(row.formation_score)} · Depth {String(row.depth_score)} · Trajectory {String(row.trajectory_score)} · Events {String(row.event_score)}</div><Provenance value="CALCULATED" /></article>)}</div>;
}

export function ReviewList({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) return <Status state="empty" message="No engineering reviews." />;
  return <div className="space-y-2">{rows.map((row) => <article key={String(row.id)} className="panel p-3 text-sm"><div>{String(row.decision)} · {String(row.engineer_name || "")}</div><p>{String(row.comment || "")}</p><div className="text-xs text-muted tech">{String(row.created_at || "")}</div></article>)}</div>;
}

export function NearbyPage() {
  const { current } = useWells();
  const [radius, setRadius] = useState(10);
  const [custom, setCustom] = useState("");
  const [formation, setFormation] = useState("");
  const [risk, setRisk] = useState("");
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tile, setTile] = useState("https://tile.openstreetmap.org/{z}/{x}/{y}.png");

  useEffect(() => { systemApi.config().then((r) => setTile(r.data.osm_tile_url)).catch(() => undefined); }, []);
  useEffect(() => {
    if (!current?.latitude || !current.longitude) return;
    setLoading(true);
    const used = custom ? Number(custom) : radius;
    wellApi.nearby({ latitude: current.latitude, longitude: current.longitude, radius: used, formation: formation || undefined, risk: risk || undefined, exclude_well_id: current.id })
      .then((r) => setRows(r.data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [current?.id, radius, custom, formation, risk]);

  if (!current) return <Status state="empty" message="Select a current well." />;
  const markers: MapWell[] = [
    { id: current.id, well_id: current.well_id, well_name: current.well_name, latitude: current.latitude || 0, longitude: current.longitude || 0, depth: current.current_depth, formation: current.formation, status: current.status, kind: "current" },
    ...rows.map((row) => ({ id: String(row.id), well_id: String(row.well_id), well_name: String(row.well_name), latitude: Number(row.latitude), longitude: Number(row.longitude), distance_km: Number(row.distance_km), depth: row.depth as number, formation: String(row.formation || ""), status: String(row.status), risk: String((row.risk_summary as { level?: string })?.level || ""), kind: "nearby" as const })),
  ];
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Nearby wells</h1>
      <p className="text-sm text-muted">Distances are calculated by PostGIS on the server.</p>
      <div className="flex flex-wrap gap-2">
        {[1, 5, 10, 25, 50].map((value) => <button key={value} className={`btn ${radius === value && !custom ? "btn-primary" : ""}`} onClick={() => { setCustom(""); setRadius(value); }}>{value} km</button>)}
        <input aria-label="Custom radius kilometres" className="field max-w-[140px]" placeholder="Custom km" value={custom} onChange={(e) => setCustom(e.target.value)} />
        <input aria-label="Formation filter" className="field max-w-[180px]" placeholder="Formation" value={formation} onChange={(e) => setFormation(e.target.value)} />
        <select aria-label="Risk filter" className="field max-w-[200px]" value={risk} onChange={(e) => setRisk(e.target.value)}>
          <option value="">Any risk history</option>
          {["MUD", "STUCK_PIPE", "KICK", "TORQUE", "CEMENTING", "LOST_CIRCULATION"].map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </div>
      {error && <Status state="error" message={error} />}
      {loading ? <Status state="loading" /> : rows.length === 0 ? <Status state="empty" message="No wells inside this radius." /> : (
        <div className="overflow-x-auto panel"><table className="w-full text-sm"><thead className="text-muted text-left"><tr><th className="p-2">Well</th><th>Distance</th><th>Formation</th><th>Depth</th><th>Status</th><th>Risk</th></tr></thead><tbody>{rows.map((row) => <tr key={String(row.id)} className="border-t border-line"><td className="p-2"><Link to={`/wells/${row.id}`}>{String(row.well_name)}</Link> <span className="tech">{String(row.well_id)}</span></td><td className="tech">{String(row.distance_km)} km</td><td>{String(row.formation || "")}</td><td className="tech">{String(row.depth ?? "")}</td><td>{String(row.status)}</td><td>{String((row.risk_summary as { level?: string })?.level || "UNKNOWN")}</td></tr>)}</tbody></table></div>
      )}
      <WellMap wells={markers} tileUrl={tile} />
    </div>
  );
}

export function MapPage() {
  const { wells, current } = useWells();
  const [radius, setRadius] = useState(25);
  const [formation, setFormation] = useState("");
  const [status, setStatus] = useState("");
  const [risk, setRisk] = useState("");
  const [nearby, setNearby] = useState<Array<Record<string, unknown>>>([]);
  const [tile, setTile] = useState("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
  const [lines, setLines] = useState<Array<{ id: string; positions: [number, number][] }>>([]);
  useEffect(() => { systemApi.config().then((r) => setTile(r.data.osm_tile_url)).catch(() => undefined); }, []);
  useEffect(() => {
    if (!current?.latitude || !current.longitude) return;
    wellApi.nearby({ latitude: current.latitude, longitude: current.longitude, radius, formation: formation || undefined, status: status || undefined, risk: risk || undefined, exclude_well_id: current.id }).then((r) => setNearby(r.data)).catch(() => setNearby([]));
    wellApi.trajectory(current.id).then((r) => setLines([{ id: current.id, positions: r.data.map((s) => [s.latitude, s.longitude]) }])).catch(() => undefined);
  }, [current?.id, radius, formation, status, risk]);
  const markers: MapWell[] = wells.filter((w) => w.latitude != null).map((w) => ({
    id: w.id,
    well_id: w.well_id,
    well_name: w.well_name,
    latitude: w.latitude as number,
    longitude: w.longitude as number,
    depth: w.current_depth,
    formation: w.formation,
    status: w.status,
    kind: w.id === current?.id ? "current" : nearby.some((n) => n.id === w.id) ? "nearby" : w.status === "COMPLETED" ? "historical" : "historical",
  }));
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">GIS map</h1>
      <div className="flex flex-wrap gap-2">
        <label className="text-sm">Radius km <input className="field w-24" value={radius} onChange={(e) => setRadius(Number(e.target.value) || 1)} /></label>
        <input aria-label="Map formation" className="field max-w-[160px]" placeholder="Formation" value={formation} onChange={(e) => setFormation(e.target.value)} />
        <input aria-label="Map status" className="field max-w-[160px]" placeholder="Status" value={status} onChange={(e) => setStatus(e.target.value)} />
        <select aria-label="Map risk" className="field max-w-[180px]" value={risk} onChange={(e) => setRisk(e.target.value)}><option value="">Risk</option>{["STUCK_PIPE", "KICK", "LOST_CIRCULATION", "TORQUE", "MUD", "CEMENTING"].map((item) => <option key={item}>{item}</option>)}</select>
      </div>
      <WellMap wells={markers} tileUrl={tile} trajectories={lines} />
    </div>
  );
}
