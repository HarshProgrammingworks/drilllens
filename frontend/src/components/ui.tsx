import { levelClass } from "../utils/access";

export function Status({ state, message }: { state: "loading" | "error" | "empty" | "idle"; message?: string }) {
  if (state === "idle") return null;
  const text = message || (state === "loading" ? "Loading…" : state === "error" ? "Something went wrong." : "No data is available.");
  return <div className={`panel p-4 text-sm ${state === "error" ? "text-crit" : "text-muted"}`} role={state === "error" ? "alert" : "status"}>{text}</div>;
}

export function Provenance({ value }: { value?: string | null }) {
  if (!value) return null;
  return <span className="text-[10px] uppercase tracking-wide border border-line rounded px-1.5 py-0.5 text-muted">{value}</span>;
}

export function RiskBadge({ level }: { level: string }) {
  return <span className={`text-xs font-semibold border rounded px-2 py-0.5 ${levelClass(level)}`}>{level || "UNKNOWN"}</span>;
}

export function Tech({ children }: { children: React.ReactNode }) {
  return <span className="tech">{children}</span>;
}

export const PARAMS: { key: string; label: string; unit: string }[] = [
  { key: "depth", label: "Depth", unit: "m" },
  { key: "rop", label: "ROP", unit: "m/h" },
  { key: "wob", label: "WOB", unit: "klbf" },
  { key: "rpm", label: "RPM", unit: "rpm" },
  { key: "torque", label: "Torque", unit: "kN·m" },
  { key: "standpipe_pressure", label: "Standpipe Pressure", unit: "psi" },
  { key: "mud_flow", label: "Mud Flow", unit: "L/min" },
  { key: "mud_weight", label: "Mud Weight", unit: "sg" },
  { key: "pump_pressure", label: "Pump Pressure", unit: "psi" },
  { key: "hook_load", label: "Hook Load", unit: "klbf" },
];
