export type Role = "ADMIN" | "DRILLING_ENGINEER" | "VIEWER";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: Role;
  permissions?: string[];
  is_active: boolean;
  last_login?: string | null;
}

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  message: string | null;
  error_code?: string;
}

export interface Well {
  id: string;
  well_id: string;
  well_name: string;
  field: string;
  operator: string;
  latitude: number | null;
  longitude: number | null;
  status: string;
  current_depth: number | null;
  formation: string | null;
  current_operation: string | null;
  spud_date?: string | null;
  completion_date?: string | null;
  well_type: string;
  trajectory_type: string;
  is_archived: boolean;
  source_type: string;
  simulate_sensors: boolean;
  demo_scenario?: string;
  updated_at?: string | null;
  distance_m?: number | null;
  risk_summary?: RiskSummary | null;
  formations?: { name: string; depth_top: number; depth_bottom: number }[];
}

export interface RiskSummary {
  level: string;
  max_score: number | null;
  top_category?: string;
  categories?: RiskCard[];
}

export interface EvidenceItem {
  id: string;
  text_excerpt: string;
  formation?: string | null;
  depth_start?: number | null;
  confidence?: number;
  well_code?: string | null;
  report_title?: string | null;
}

export interface RiskCard {
  category: string;
  label: string;
  score: number;
  level: string;
  confidence: number;
  confidence_meaning?: string;
  reasons: string[];
  evidence?: EvidenceItem[];
  evidence_ids?: string[];
  evidence_count: number;
  timestamp?: string;
  current_data?: Record<string, number | null>;
  baseline?: Record<string, number | null>;
  provenance?: string;
  engine?: string;
}

export interface ParameterPoint {
  timestamp: string;
  depth: number;
  rop: number;
  wob: number;
  rpm: number;
  torque: number;
  standpipe_pressure: number;
  mud_flow: number;
  mud_weight: number;
  pump_pressure: number;
  hook_load: number;
  source: string;
  provenance: string;
}

export interface LiveMessage {
  well_id: string;
  well_uuid: string;
  timestamp: string;
  source: string;
  label: string;
  scenario: string;
  parameters: Record<string, number>;
  units: Record<string, string>;
}
