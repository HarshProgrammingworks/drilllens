import { FormEvent, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ParameterChart } from "../charts/ParameterChart";
import { Provenance, RiskBadge, Status } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useWells } from "../context/WellContext";
import { EventTable, ReviewList, SimilarityTable } from "./OperationsPages";
import { alertApi, authApi, evidenceApi, reportApi, reviewApi, riskApi, searchApi, wellApi } from "../services/api";
import type { RiskCard } from "../types";
import { canWrite } from "../utils/access";

export function ReportsPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    reportApi.list({ q, status: status || undefined, report_type: type || undefined, page: 1, page_size: 50 })
      .then((r) => setRows(r.data.items)).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [q, status, type]);
  return (
    <div className="space-y-3">
      <div className="flex justify-between"><h1 className="text-xl font-semibold">Historical reports</h1><Link className="btn" to="/reports/upload">Upload</Link></div>
      <div className="flex gap-2"><input aria-label="Search reports" className="field max-w-xs" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title" /><select aria-label="Status" className="field max-w-[180px]" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Status</option>{["UPLOADED", "OCR_PROCESSING", "NLP_PROCESSING", "STRUCTURING", "INDEXING", "COMPLETED", "FAILED"].map((s) => <option key={s}>{s}</option>)}</select><select aria-label="Type" className="field max-w-[140px]" value={type} onChange={(e) => setType(e.target.value)}><option value="">Type</option><option>WCR</option><option>DDR</option><option>OTHER</option></select></div>
      {error && <Status state="error" message={error} />}
      {loading ? <Status state="loading" /> : rows.length === 0 ? <Status state="empty" message="No reports." /> : (
        <div className="overflow-x-auto panel"><table className="w-full text-sm"><thead className="text-muted text-left"><tr><th className="p-2">Title</th><th>Well</th><th>Type</th><th>Date</th><th>Pages</th><th>Status</th></tr></thead><tbody>{rows.map((row) => <tr key={String(row.id)} className="border-t border-line"><td className="p-2"><Link className="text-info" to={`/reports/${row.id}`}>{String(row.title)}</Link></td><td className="tech">{String(row.well_code || "")}</td><td>{String(row.report_type)}</td><td>{String(row.report_date || "")}</td><td>{String(row.page_count)}</td><td>{String(row.status)} ({String(row.progress)}%)</td></tr>)}</tbody></table></div>
      )}
    </div>
  );
}

export function UploadPage() {
  const { wells } = useWells();
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  if (!canWrite(user?.role)) return <Status state="error" message="You do not have permission to upload reports." />;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setLoading(true); setError("");
    try {
      const response = await reportApi.upload(data);
      setMessage(`Stored ${String(response.data.title)}. Status ${String(response.data.status)}.`);
      event.currentTarget.reset();
    } catch (err) { setError(err instanceof Error ? err.message : "Upload failed"); }
    finally { setLoading(false); }
  }
  return (
    <form className="panel p-4 max-w-xl space-y-3" onSubmit={submit}>
      <h1 className="text-xl font-semibold">Upload report</h1>
      <p className="text-sm text-muted">PDF, scanned PDF, TXT, or CSV. Processing runs OCR only when a page has little embedded text.</p>
      <input className="field" name="title" placeholder="Title" required />
      <select className="field" name="report_type" defaultValue="WCR"><option>WCR</option><option>DDR</option><option>OTHER</option></select>
      <select className="field" name="well_id"><option value="">Unassigned</option>{wells.map((w) => <option key={w.id} value={w.well_id}>{w.well_id} · {w.well_name}</option>)}</select>
      <input className="field" type="date" name="report_date" />
      <input aria-label="Report file" className="field" type="file" name="file" accept=".pdf,.txt,.csv" required />
      {error && <Status state="error" message={error} />}
      {message && <p className="text-sm text-ok">{message}</p>}
      <button className="btn btn-primary" disabled={loading}>{loading ? "Uploading…" : "Upload"}</button>
    </form>
  );
}

export function ReportDetailPage() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [pages, setPages] = useState<Array<Record<string, unknown>>>([]);
  const [entities, setEntities] = useState<Array<Record<string, unknown>>>([]);
  const [ocr, setOcr] = useState<Array<Record<string, unknown>>>([]);
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  async function load() {
    try {
      const item = await reportApi.get(id);
      setReport(item.data);
      if (item.data.well_id) wellApi.events(String(item.data.well_id)).then((r) => setEvents(r.data.filter((e) => e.report_id === id))).catch(() => undefined);
      const [p, e, o] = await Promise.all([reportApi.pages(id), reportApi.entities(id), reportApi.ocr(id)]);
      setPages(p.data); setEntities(e.data); setOcr(o.data);
      return String(item.data.status);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); return "FAILED"; }
  }
  useEffect(() => {
    let timer = 0;
    let cancelled = false;
    async function poll() {
      const status = await load();
      if (!cancelled && status !== "COMPLETED" && status !== "FAILED") timer = window.setTimeout(poll, 2000);
    }
    poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [id]);
  if (error) return <Status state="error" message={error} />;
  if (!report) return <Status state="loading" />;
  const done = report.status === "COMPLETED" || report.status === "FAILED";
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{String(report.title)}</h1>
      <div className="panel p-3 text-sm grid md:grid-cols-4 gap-2">
        <div>Status {String(report.status)}</div><div>Progress {String(report.progress)}%</div><div>Type {String(report.report_type)}</div><div className="tech">{String(report.well_code || "Unassigned")}</div>
        <Provenance value={String(report.source_type || "")} />
      </div>
      {!done && <Status state="loading" message={`Processing ${String(report.status)} (${String(report.progress)}%).`} />}
      {report.error_message ? <Status state="error" message={String(report.error_message)} /> : null}
      <div className="h-2 bg-slate-800 rounded"><div className="h-2 bg-info rounded" style={{ width: `${Number(report.progress) || 0}%` }} /></div>
      <button className="btn" onClick={() => reportApi.openFile(id)}>Open source file</button>
      <section><h2 className="font-medium mb-2">Extracted text</h2>{pages.map((p) => <pre key={String(p.id)} className="panel p-3 text-xs whitespace-pre-wrap mb-2">Page {String(p.page_number)} {p.is_scanned ? "(OCR)" : "(embedded text)"}\n{String(p.text_content)}</pre>)}</section>
      <section><h2 className="font-medium mb-2">OCR</h2>{ocr.length === 0 ? <Status state="empty" message="No OCR step was required or stored." /> : ocr.map((row, i) => <pre key={i} className="panel p-3 text-xs whitespace-pre-wrap">Page {String(row.page_number)} confidence {String(row.confidence)} status {String(row.status)}\n{String(row.raw_ocr_text)}</pre>)}</section>
      <section><h2 className="font-medium mb-2">Entities</h2>{entities.length === 0 ? <Status state="empty" message="No entities extracted." /> : <div className="overflow-x-auto panel"><table className="w-full text-sm"><tbody>{entities.map((e) => <tr key={String(e.id)} className="border-t border-line"><td className="p-2">{String(e.entity_type)}</td><td>{String(e.text)}</td><td className="tech">{String(e.confidence)}</td><td>{String(e.extractor)}</td></tr>)}</tbody></table></div>}</section>
      <section><h2 className="font-medium mb-2">Drilling events from this report</h2><EventTable rows={events} /></section>
    </div>
  );
}

export function ComparisonPage() {
  const { wells, current } = useWells();
  const [other, setOther] = useState("");
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [pair, setPair] = useState<Record<string, unknown> | null>(null);
  const [corr, setCorr] = useState<Record<string, unknown> | null>(null);
  const [tolerance, setTolerance] = useState(150);
  const [correction, setCorrection] = useState(0);
  const [formation, setFormation] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!current) return;
    wellApi.similar(current.id).then((r) => setRows(r.data)).catch((e) => setError(e.message));
  }, [current?.id]);
  if (!current) return <Status state="empty" message="Select a well." />;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Well comparison</h1>
      <p className="text-sm text-muted">Scores are calculated in the backend from configurable weights. Source depths are never overwritten.</p>
      {error && <Status state="error" message={error} />}
      <SimilarityTable rows={rows} />
      <div className="flex flex-wrap gap-2 items-end">
        <select aria-label="Compare with" className="field max-w-xs" value={other} onChange={(e) => setOther(e.target.value)}><option value="">Compare with…</option>{wells.filter((w) => w.id !== current.id).map((w) => <option key={w.id} value={w.id}>{w.well_id}</option>)}</select>
        <button className="btn" disabled={!other} onClick={() => wellApi.compare(current.id, other).then((r) => setPair(r.data))}>Calculate</button>
      </div>
      {pair && <article className="panel p-3 text-sm"><div className="tech text-lg">{Number(pair.overall_score).toFixed(3)}</div><p>{String(pair.explanation)}</p><Provenance value="CALCULATED" /></article>}
      <section className="panel p-4 space-y-2">
        <h2 className="font-medium">Depth correlation</h2>
        <div className="flex flex-wrap gap-2">
          <label className="text-sm">Tolerance m <input className="field w-28" type="number" value={tolerance} onChange={(e) => setTolerance(Number(e.target.value))} /></label>
          <label className="text-sm">Correction m <input className="field w-28" type="number" value={correction} onChange={(e) => setCorrection(Number(e.target.value))} /></label>
          <input aria-label="Formation match" className="field max-w-[180px]" placeholder="Formation" value={formation} onChange={(e) => setFormation(e.target.value)} />
          <button className="btn" onClick={() => wellApi.correlation(current.id, { tolerance, correction_m: correction, formation: formation || undefined, depth: current.current_depth || undefined }).then((r) => setCorr(r.data))}>Compare depths</button>
        </div>
        {corr && <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-muted text-left"><tr><th>Well</th><th>Current</th><th>Historical</th><th>Adjusted</th><th>Difference</th><th>Formation</th><th>Event</th><th>Uncertainty</th></tr></thead><tbody>{((corr.matches as Array<Record<string, unknown>>) || []).map((row) => <tr key={String(row.event_id)} className="border-t border-line"><td className="tech">{String(row.well_code)}</td><td className="tech">{String(row.current_depth)}</td><td className="tech">{String(row.historical_depth)}</td><td className="tech">{String(row.adjusted_comparison_depth)}</td><td className="tech">{String(row.depth_difference)}</td><td>{String(row.formation || "")}</td><td>{String(row.event_type)}</td><td className="tech">{String(row.uncertainty)}</td></tr>)}</tbody></table>{((corr.matches as unknown[]) || []).length === 0 && <Status state="empty" message="No events inside the tolerance." />}<p className="text-xs text-muted mt-2">Original historical depth stays in the database. Correction is a comparison view only.</p></div>}
      </section>
    </div>
  );
}

export function RiskPage() {
  const { current } = useWells();
  const { user } = useAuth();
  const [rows, setRows] = useState<RiskCard[]>([]);
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  async function load() {
    if (!current) return;
    const [c, h] = await Promise.all([riskApi.current(current.id), riskApi.history(current.id)]);
    setRows(c.data || []);
    setHistory(h.data);
  }
  useEffect(() => { load().catch((e) => setError(e.message)); }, [current?.id]);
  if (!current) return <Status state="empty" message="Select a well." />;
  return (
    <div className="space-y-4">
      <div className="flex justify-between"><h1 className="text-xl font-semibold">Risk analysis</h1>{canWrite(user?.role) && <button className="btn btn-primary" disabled={loading} onClick={async () => { setLoading(true); setError(""); try { const r = await riskApi.analyze(current.id); setRows(r.data); setMessage(r.message || "Analysis stored."); await load(); } catch (e) { setError(e instanceof Error ? e.message : "Failed"); } finally { setLoading(false); } }}>{loading ? "Calculating…" : "Run rule-based analysis"}</button>}</div>
      <p className="text-sm text-muted">Transparent rules. Confidence is analytical confidence, not certainty that an event will occur. No accuracy percentage is claimed.</p>
      {message && <p className="text-sm">{message}</p>}
      {error && <Status state="error" message={error} />}
      {!rows.length && <Status state="empty" message="No current indicators stored." />}
      <div className="grid md:grid-cols-2 gap-3">{rows.map((risk) => (
        <article key={risk.category} className="panel p-4 space-y-2">
          <div className="flex justify-between"><h2>{risk.label}</h2><RiskBadge level={risk.level} /></div>
          <div className="tech text-3xl">{risk.score}</div>
          <div className="text-sm">Confidence {risk.confidence}</div>
          <ul className="text-sm list-disc pl-4">{risk.reasons?.map((reason) => <li key={reason}>{reason}</li>)}</ul>
          <div className="text-xs text-muted tech">{risk.timestamp}</div>
          <Provenance value="RULE-BASED" />
          <div className="text-sm">Evidence {risk.evidence_count}{(risk.evidence || []).map((ev) => <div key={ev.id}><Link className="text-info" to={`/evidence/${ev.id}`}>{ev.text_excerpt.slice(0, 140)}</Link></div>)}</div>
        </article>
      ))}</div>
      <ParameterChart title="Risk score history" rows={history.map((h) => ({ timestamp: String(h.timestamp), score: Number(h.score), depth: Number(h.depth || 0) }))} xKey="depth" series={[{ key: "score", label: "Score" }]} />
    </div>
  );
}

export function AlertsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  async function load() {
    const response = await alertApi.list({ status: status || undefined, page: 1, page_size: 50 });
    setRows(response.data.items);
  }
  useEffect(() => { load().catch((e) => setError(e.message)); }, [status]);
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Alerts</h1>
      <select aria-label="Alert status" className="field max-w-[200px]" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All</option>{["OPEN", "ACKNOWLEDGED", "REVIEWED", "ESCALATED", "FALSE_POSITIVE", "RESOLVED"].map((s) => <option key={s}>{s}</option>)}</select>
      {error && <Status state="error" message={error} />}
      {rows.length === 0 && <Status state="empty" message="No alerts." />}
      {rows.map((row) => (
        <article key={String(row.id)} className="panel p-3 text-sm space-y-2">
          <div className="flex justify-between"><strong>{String(row.title)}</strong><RiskBadge level={String(row.severity)} /></div>
          <p>{String(row.description)}</p>
          <div className="text-xs text-muted tech">{String(row.well_code)} · score {String(row.score)} · {String(row.status)} · {String(row.created_at)}</div>
          <Provenance value={String(row.trigger_source)} />
          {canWrite(user?.role) && (
            <div className="flex flex-wrap gap-2">
              <input aria-label="Alert note" className="field max-w-xs" placeholder="Note" value={note} onChange={(e) => setNote(e.target.value)} />
              {[["acknowledge", "Acknowledge"], ["review", "Review"], ["escalate", "Escalate"], ["false-positive", "Mark false positive"]].map(([action, label]) => (
                <button key={action} className="btn" onClick={async () => { await alertApi.act(String(row.id), action, note); await load(); }}>{label}</button>
              ))}
            </div>
          )}
        </article>
      ))}
    </div>
  );
}

export function EvidencePage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "stuck pipe");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [item, setItem] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!id) return;
    evidenceApi.source(id).then((r) => setItem(r.data)).catch((e) => setError(e.message));
  }, [id]);
  async function run(event?: FormEvent) {
    event?.preventDefault();
    setError("");
    try { setResult((await searchApi.query(q)).data); } catch (e) { setError(e instanceof Error ? e.message : "Search failed"); }
  }
  useEffect(() => { if (!id) run(); }, [id]);
  if (id) {
    if (error) return <Status state="error" message={error} />;
    if (!item) return <Status state="loading" />;
    return (
      <article className="panel p-4 space-y-2 text-sm">
        <h1 className="text-xl font-semibold">Evidence</h1>
        <div>Report: {item.report_id ? <Link className="text-info" to={`/reports/${item.report_id}`}>{String(item.report_title)}</Link> : "Seed record"}</div>
        <div>Page / location: {String(item.source_location || "")}</div>
        <div>Well: <Link className="text-info" to={`/wells/${item.well_id}`}>{String(item.well_name)} </Link><span className="tech">{String(item.well_code || "")}</span></div>
        <div>Depth: <span className="tech">{String(item.depth_start)}–{String(item.depth_end)}</span> m</div>
        <div>Formation: {String(item.formation || "")}</div>
        <div>Event: {String(item.event_type || "")}</div>
        <p className="whitespace-pre-wrap">{String(item.text_excerpt)}</p>
        <Provenance value={String(item.source_type)} />
        {item.report_id ? <button className="btn" onClick={() => reportApi.openFile(String(item.report_id))}>Source document</button> : null}
      </article>
    );
  }
  const events = (result?.events as Array<Record<string, unknown>>) || [];
  const evidence = (result?.evidence as Array<Record<string, unknown>>) || [];
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Evidence search</h1>
      <form className="flex gap-2" onSubmit={run}><input aria-label="Evidence query" className="field" value={q} onChange={(e) => setQ(e.target.value)} /><button className="btn btn-primary">Search</button></form>
      {error && <Status state="error" message={error} />}
      {!result && <Status state="loading" />}
      {result && events.length + evidence.length === 0 && <Status state="empty" message="No matches." />}
      {evidence.map((row) => <article key={String(row.id)} className="panel p-3 text-sm"><Link className="text-info" to={`/evidence/${row.id}`}>{highlight(String(row.text_excerpt), q)}</Link><div className="text-xs text-muted">{String(row.well_code || "")} · {String(row.formation || "")} · {String(row.report_title || "")}</div></article>)}
      {events.map((row) => <article key={String(row.id)} className="panel p-3 text-sm"><Link to={`/wells/${row.well_id}`}>{String(row.well_code)}</Link> · {String(row.event_type)} · <span className="tech">{String(row.depth_start || "")} m</span><p>{highlight(String(row.description), q)}</p></article>)}
    </div>
  );
}

function highlight(text: string, q: string) {
  const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig"));
  return parts.map((part, index) => part.toLowerCase() === q.toLowerCase() ? <mark key={index} className="bg-warn/40 text-white">{part}</mark> : <span key={index}>{part}</span>);
}

export function ReviewPage() {
  const { current } = useWells();
  const { user } = useAuth();
  const [risks, setRisks] = useState<RiskCard[]>([]);
  const [alerts, setAlerts] = useState<Array<Record<string, unknown>>>([]);
  const [reviews, setReviews] = useState<Array<Record<string, unknown>>>([]);
  const [similar, setSimilar] = useState<Array<Record<string, unknown>>>([]);
  const [comment, setComment] = useState("");
  const [decision, setDecision] = useState("REVIEW");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function load() {
    if (!current) return;
    const [r, a, v, s] = await Promise.all([riskApi.current(current.id), alertApi.list({ well_id: current.well_id, page_size: 10 }), reviewApi.list({ well_id: current.id }), wellApi.similar(current.id)]);
    setRisks(r.data || []); setAlerts(a.data.items); setReviews(v.data); setSimilar(s.data);
  }
  useEffect(() => { load().catch((e) => setError(e.message)); }, [current?.id]);
  if (!current) return <Status state="empty" message="Select a well." />;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Engineering review</h1>
      <p className="text-sm text-muted">Review records a human decision. DrillLens does not authorize an operation or change a drilling parameter.</p>
      {error && <Status state="error" message={error} />}
      <div className="grid lg:grid-cols-2 gap-3">
        <section className="space-y-2">{risks.map((risk) => <article key={risk.category} className="panel p-3 text-sm"><div className="flex justify-between">{risk.label}<RiskBadge level={risk.level} /></div><p>{risk.reasons?.[0]}</p>{risk.evidence?.[0] && <Link className="text-info" to={`/evidence/${risk.evidence[0].id}`}>Evidence</Link>}</article>)}</section>
        <SimilarityTable rows={similar.slice(0, 3)} />
      </div>
      <section className="panel p-3 text-sm"><h2 className="font-medium mb-2">Open alerts</h2>{alerts.length === 0 && <p className="text-muted">None for this well.</p>}{alerts.map((a) => <div key={String(a.id)}>{String(a.title)} · {String(a.status)}</div>)}</section>
      {canWrite(user?.role) ? (
        <form className="panel p-4 space-y-2" onSubmit={async (e) => {
          e.preventDefault();
          try {
            const response = await reviewApi.create({ well_id: current.id, alert_id: alerts[0]?.id, decision, comment, risk_category: risks[0]?.category });
            setMessage(response.message || "Review stored.");
            setComment("");
            await load();
          } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
        }}>
          <label className="text-sm block">Decision
            <select className="field mt-1" value={decision} onChange={(e) => setDecision(e.target.value)}>
              <option value="ACKNOWLEDGE">Acknowledge</option>
              <option value="REVIEW">Review</option>
              <option value="COMMENT">Add comment</option>
              <option value="FALSE_POSITIVE">Mark false positive</option>
              <option value="ESCALATE">Escalate</option>
            </select>
          </label>
          <textarea aria-label="Review comment" className="field min-h-24" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Engineering comment" />
          <button className="btn btn-primary">Store review</button>
          {message && <p className="text-sm text-ok">{message}</p>}
        </form>
      ) : <Status state="empty" message="Viewers can read reviews. Creating a review requires a drilling engineer or administrator." />}
      <ReviewList rows={reviews} />
    </div>
  );
}

export function ReportsDashboardPage() {
  const [stats, setStats] = useState<{ total: number; by_status: Record<string, number>; by_type: Record<string, number> } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { reportApi.stats().then((r) => setStats(r.data)).catch((e) => setError(e.message)); }, []);
  if (error) return <Status state="error" message={error} />;
  if (!stats) return <Status state="loading" />;
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Report processing</h1>
      <div className="tech text-3xl">{stats.total}</div>
      <div className="grid md:grid-cols-2 gap-3">
        <section className="panel p-3">{Object.entries(stats.by_status).map(([k, v]) => <div key={k} className="flex justify-between text-sm"><span>{k}</span><span className="tech">{v}</span></div>)}{Object.keys(stats.by_status).length === 0 && <Status state="empty" message="No reports." />}</section>
        <section className="panel p-3">{Object.entries(stats.by_type).map(([k, v]) => <div key={k} className="flex justify-between text-sm"><span>{k}</span><span className="tech">{v}</span></div>)}</section>
      </div>
    </div>
  );
}

export function SettingsPage() {
  const { user, refresh } = useAuth();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  return (
    <div className="max-w-lg space-y-4">
      <h1 className="text-xl font-semibold">Settings</h1>
      <section className="panel p-4 text-sm space-y-1">
        <div>{user?.full_name}</div>
        <div className="tech">{user?.username}</div>
        <div>{user?.email}</div>
        <div>Role {user?.role}</div>
        <button className="btn mt-2" onClick={() => refresh().then(() => setMessage("Profile reloaded."))}>Reload profile</button>
      </section>
      <form className="panel p-4 space-y-2" onSubmit={async (e) => {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        setError("");
        try {
          await authApi.changePassword(String(data.get("current")), String(data.get("next")));
          setMessage("Password updated.");
        } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
      }}>
        <h2 className="font-medium">Change password</h2>
        <input className="field" type="password" name="current" placeholder="Current password" required />
        <input className="field" type="password" name="next" placeholder="New password" minLength={8} required />
        <button className="btn">Update</button>
      </form>
      {message && <p className="text-sm text-ok">{message}</p>}
      {error && <Status state="error" message={error} />}
      <section className="text-xs text-muted">
        <p>DrillLens · Powered by eRTMAC-NWIS</p>
        <p className="mt-2">Enhanced Real-Time Monitoring &amp; Control Centre – Nearby Well Intelligence System. The platform provides engineering intelligence. It does not autonomously control drilling equipment, change parameters, or authorize operations.</p>
      </section>
    </div>
  );
}
