import { createContext, useContext, useEffect, useState } from "react";
import { wellApi } from "../services/api";
import type { Well } from "../types";
import { useAuth } from "./AuthContext";

interface WellState {
  wells: Well[];
  current: Well | null;
  loading: boolean;
  error: string;
  select: (id: string) => Promise<void>;
  reload: () => Promise<void>;
}

const WellContext = createContext<WellState | null>(null);
const KEY = "drilllens_well";

export function WellProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [wells, setWells] = useState<Well[]>([]);
  const [current, setCurrent] = useState<Well | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function reload() {
    setLoading(true);
    setError("");
    try {
      const response = await wellApi.list({ page: 1, page_size: 100, sort: "well_id" });
      const items = response.data?.items || [];
      setWells(items);
      if (items.length > 0) {
        const saved = localStorage.getItem(KEY);
        const match = items.find((item) => item.id === saved || item.well_id === saved) || items.find((item) => item.simulate_sensors) || items[0];
        if (match) {
          try {
            const detail = await wellApi.get(match.id);
            setCurrent(detail.data);
            localStorage.setItem(KEY, match.id);
          } catch {
            setCurrent(match);
          }
        } else {
          setCurrent(null);
        }
      } else {
        setCurrent(null);
      }
    } catch (err) {
      setWells([]);
      setCurrent(null);
      const msg = err instanceof Error ? err.message : "Failed to load well records from the database.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function select(id: string) {
    try {
      const detail = await wellApi.get(id);
      setCurrent(detail.data);
      localStorage.setItem(KEY, id);
    } catch (err) {
      const match = wells.find((w) => w.id === id || w.well_id === id);
      if (match) {
        setCurrent(match);
        localStorage.setItem(KEY, match.id);
      }
      setError(err instanceof Error ? err.message : "Failed to load well details");
    }
  }

  useEffect(() => {
    if (user) reload();
    else {
      setWells([]);
      setCurrent(null);
    }
  }, [user]);

  return <WellContext.Provider value={{ wells, current, loading, error, select, reload }}>{children}</WellContext.Provider>;
}

export function useWells() {
  const ctx = useContext(WellContext);
  if (!ctx) throw new Error("WellProvider is required");
  return ctx;
}
