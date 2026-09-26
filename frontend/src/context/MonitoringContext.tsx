import { createContext, useContext, useEffect, useState } from "react";
import { getToken } from "../api/client";
import { monitoringSocket, wellApi } from "../services/api";
import type { LiveMessage, ParameterPoint } from "../types";
import { useWells } from "./WellContext";

interface MonitorState {
  live: LiveMessage | null;
  history: ParameterPoint[];
  connected: boolean;
  error: string;
  reloadHistory: () => Promise<void>;
}

const MonitoringContext = createContext<MonitorState | null>(null);

export function MonitoringProvider({ children }: { children: React.ReactNode }) {
  const { current } = useWells();
  const [live, setLive] = useState<LiveMessage | null>(null);
  const [history, setHistory] = useState<ParameterPoint[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  async function reloadHistory() {
    if (!current) return;
    const response = await wellApi.parameters(current.id);
    setHistory(response.data);
  }

  useEffect(() => {
    if (!current) return;
    setLive(null);
    reloadHistory().catch((err) => setError(err instanceof Error ? err.message : "Parameter history failed"));
    const token = getToken();
    if (!token || !current.simulate_sensors) {
      setConnected(false);
      return;
    }
    setConnected(true);
    const close = monitoringSocket(current.well_id, token, (message) => {
      setLive(message);
      setHistory((prev) => {
        const point: ParameterPoint = {
          timestamp: message.timestamp,
          depth: message.parameters.depth,
          rop: message.parameters.rop,
          wob: message.parameters.wob,
          rpm: message.parameters.rpm,
          torque: message.parameters.torque,
          standpipe_pressure: message.parameters.standpipe_pressure,
          mud_flow: message.parameters.mud_flow,
          mud_weight: message.parameters.mud_weight,
          pump_pressure: message.parameters.pump_pressure,
          hook_load: message.parameters.hook_load,
          source: message.source,
          provenance: "SIMULATED",
        };
        return [...prev, point].slice(-400);
      });
    });
    return close;
  }, [current?.id]);

  return <MonitoringContext.Provider value={{ live, history, connected, error, reloadHistory }}>{children}</MonitoringContext.Provider>;
}

export function useMonitoring() {
  const ctx = useContext(MonitoringContext);
  if (!ctx) throw new Error("MonitoringProvider is required");
  return ctx;
}
