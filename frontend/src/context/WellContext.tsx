import { createContext, useContext, useEffect, useState } from "react";
import { wellApi } from "../services/api";
import type { Well } from "../types";
import { useAuth } from "./AuthContext";

const DEMO_WELLS: Well[] = [
  {
    id: "w-demo-001",
    well_id: "WL-001",
    well_name: "North Rift 1",
    field: "North Rift",
    operator: "Rift Energy",
    latitude: 31.85,
    longitude: -102.35,
    status: "DRILLING",
    current_depth: 2450,
    formation: "Wolfcamp",
    current_operation: "Drilling ahead with 8-1/2 inch assembly",
    spud_date: "2024-01-15",
    completion_date: null,
    well_type: "DEVELOPMENT",
    trajectory_type: "DIRECTIONAL",
    is_archived: false,
    source_type: "DEMO",
    simulate_sensors: true,
    demo_scenario: "KICK_WARNING",
    updated_at: new Date().toISOString(),
    risk_summary: {
      level: "HIGH",
      max_score: 74,
      top_category: "WELLBORE_STABILITY",
      categories: [
        {
          category: "WELLBORE_STABILITY",
          label: "Wellbore Stability Alert",
          score: 74,
          level: "HIGH",
          confidence: 0.88,
          reasons: [
            "Tight hole indicators with elevated torque fluctuations in Wolfcamp interval.",
            "Cycle mud weight and monitor ECD prior to next stand.",
          ],
          evidence_count: 2,
        },
      ],
    },
    formations: [
      { name: "Wolfcamp", depth_top: 2200, depth_bottom: 2700 },
      { name: "Bone Spring", depth_top: 1800, depth_bottom: 2200 },
    ],
  },
  {
    id: "w-demo-002",
    well_id: "WL-002",
    well_name: "North Rift 2",
    field: "North Rift",
    operator: "Rift Energy",
    latitude: 31.872,
    longitude: -102.348,
    status: "COMPLETED",
    current_depth: 2680,
    formation: "Bone Spring",
    current_operation: "Completed / Active monitoring",
    spud_date: "2023-08-10",
    completion_date: "2023-11-20",
    well_type: "DEVELOPMENT",
    trajectory_type: "DIRECTIONAL",
    is_archived: false,
    source_type: "DEMO",
    simulate_sensors: false,
    updated_at: new Date().toISOString(),
    risk_summary: {
      level: "LOW",
      max_score: 18,
      top_category: "NONE",
      categories: [],
    },
  },
];

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
    } catch {
      // In offline / MVP demo mode, load demo wells so application operates smoothly
      setWells(DEMO_WELLS);
      const saved = localStorage.getItem(KEY);
      const match = DEMO_WELLS.find((item) => item.id === saved) || DEMO_WELLS[0];
      setCurrent(match);
      if (match) localStorage.setItem(KEY, match.id);
    } finally {
      setLoading(false);
    }
  }

  async function select(id: string) {
    try {
      const detail = await wellApi.get(id);
      setCurrent(detail.data);
      localStorage.setItem(KEY, id);
    } catch {
      const match = DEMO_WELLS.find((w) => w.id === id);
      if (match) {
        setCurrent(match);
        localStorage.setItem(KEY, id);
      }
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
