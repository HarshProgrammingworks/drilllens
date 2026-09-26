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
      const items = response.data.items;
      setWells(items);
      const saved = localStorage.getItem(KEY);
      const match = items.find((item) => item.id === saved) || items.find((item) => item.simulate_sensors) || items[0];
      if (match) {
        const detail = await wellApi.get(match.id);
        setCurrent(detail.data);
        localStorage.setItem(KEY, match.id);
      } else setCurrent(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load wells");
    } finally {
      setLoading(false);
    }
  }

  async function select(id: string) {
    const detail = await wellApi.get(id);
    setCurrent(detail.data);
    localStorage.setItem(KEY, id);
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
