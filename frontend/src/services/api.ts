import { api } from "../api/client";
import type { ApiEnvelope, LiveMessage, ParameterPoint, RiskCard, User, Well } from "../types";

async function unwrap<T>(promise: Promise<{ data: ApiEnvelope<T> }>) {
  const response = await promise;
  return response.data;
}

export const authApi = {
  login: (username: string, password: string, remember: boolean) =>
    unwrap<{ access_token: string; user: User }>(api.post("/auth/login", { username, password, remember })),
  me: () => unwrap<User>(api.get("/auth/me")),
  logout: () => unwrap<{ logged_out: boolean }>(api.post("/auth/logout")),
  forgot: (email: string) => unwrap<{ development_reset_token?: string; notice?: string }>(api.post("/auth/forgot-password", { email })),
  reset: (token: string, password: string) => unwrap<{ reset: boolean }>(api.post("/auth/reset-password", { token, password })),
  changePassword: (current_password: string, new_password: string) =>
    unwrap<{ changed: boolean }>(api.post("/auth/change-password", { current_password, new_password })),
};

export const wellApi = {
  list: (params: Record<string, string | number | boolean | undefined>) =>
    unwrap<{ items: Well[]; total: number }>(api.get("/wells", { params })),
  get: (id: string) => unwrap<Well>(api.get(`/wells/${id}`)),
  create: (body: Record<string, unknown>) => unwrap<Well>(api.post("/wells", body)),
  update: (id: string, body: Record<string, unknown>) => unwrap<Well>(api.put(`/wells/${id}`, body)),
  archive: (id: string) => unwrap<Well>(api.delete(`/wells/${id}`)),
  nearby: (params: Record<string, string | number | undefined>) => unwrap<Array<Record<string, unknown>>>(api.get("/wells/nearby", { params })),
  events: (id: string) => unwrap<Array<Record<string, unknown>>>(api.get(`/wells/${id}/events`)),
  trajectory: (id: string) => unwrap<Array<Record<string, number>>>(api.get(`/wells/${id}/trajectory`)),
  similar: (id: string) => unwrap<Array<Record<string, unknown>>>(api.get(`/wells/${id}/similar`)),
  compare: (id: string, other: string) => unwrap<Record<string, unknown>>(api.get(`/wells/${id}/compare/${other}`)),
  correlation: (id: string, params: Record<string, string | number | undefined>) =>
    unwrap<Record<string, unknown>>(api.get(`/wells/${id}/depth-correlation`, { params })),
  parameters: (id: string) => unwrap<ParameterPoint[]>(api.get(`/wells/${id}/parameters`)),
  latest: (id: string) => unwrap<{ timestamp: string; source: string; provenance: string; parameters: Record<string, { value: number; unit: string }> } | null>(api.get(`/wells/${id}/parameters/latest`)),
  reviews: (id: string) => unwrap<Array<Record<string, unknown>>>(api.get(`/wells/${id}/reviews`)),
};

export const reportApi = {
  list: (params: Record<string, string | number | undefined>) => unwrap<{ items: Array<Record<string, unknown>>; total: number }>(api.get("/reports", { params })),
  stats: () => unwrap<{ total: number; by_status: Record<string, number>; by_type: Record<string, number> }>(api.get("/reports/stats")),
  get: (id: string) => unwrap<Record<string, unknown>>(api.get(`/reports/${id}`)),
  pages: (id: string) => unwrap<Array<Record<string, unknown>>>(api.get(`/reports/${id}/pages`)),
  entities: (id: string) => unwrap<Array<Record<string, unknown>>>(api.get(`/reports/${id}/entities`)),
  ocr: (id: string) => unwrap<Array<Record<string, unknown>>>(api.get(`/reports/${id}/ocr`)),
  upload: (form: FormData) => unwrap<Record<string, unknown>>(api.post("/reports/upload", form)),
  reprocess: (id: string) => unwrap<Record<string, unknown>>(api.post(`/reports/${id}/process`)),
  openFile: async (id: string) => {
    const response = await api.get(`/reports/${id}/file`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    window.open(url, "_blank");
  },
};

export const riskApi = {
  current: (wellId: string) => unwrap<RiskCard[]>(api.get("/risk/current", { params: { well_id: wellId } })),
  history: (wellId: string, category?: string) => unwrap<Array<Record<string, unknown>>>(api.get("/risk/history", { params: { well_id: wellId, category } })),
  analyze: (wellId: string) => unwrap<RiskCard[]>(api.post("/risk/analyze", { well_id: wellId })),
};

export const alertApi = {
  list: (params: Record<string, string | number | undefined>) => unwrap<{ items: Array<Record<string, unknown>>; total: number }>(api.get("/alerts", { params })),
  get: (id: string) => unwrap<Record<string, unknown>>(api.get(`/alerts/${id}`)),
  act: (id: string, action: string, note?: string) => unwrap<Record<string, unknown>>(api.post(`/alerts/${id}/${action}`, { note })),
};

export const evidenceApi = {
  get: (id: string) => unwrap<Record<string, unknown>>(api.get(`/evidence/${id}`)),
  source: (id: string) => unwrap<Record<string, unknown>>(api.get(`/evidence/${id}/source`)),
};

export const searchApi = {
  query: (q: string) => unwrap<Record<string, unknown>>(api.get("/search", { params: { q } })),
};

export const reviewApi = {
  list: (params?: Record<string, string | undefined>) => unwrap<Array<Record<string, unknown>>>(api.get("/reviews", { params })),
  create: (body: Record<string, unknown>) => unwrap<Record<string, unknown>>(api.post("/reviews", body)),
  update: (id: string, body: Record<string, unknown>) => unwrap<Record<string, unknown>>(api.put(`/reviews/${id}`, body)),
};

export const systemApi = {
  config: () => unwrap<Record<string, string>>(api.get("/system/public-config")),
  notifications: () => unwrap<Array<Record<string, unknown>>>(api.get("/notifications")),
  read: (id: string) => unwrap<unknown>(api.post(`/notifications/${id}/read`)),
  scenario: (wellId: string, scenario: string) => unwrap<unknown>(api.post(`/monitoring/${wellId}/demo-scenario`, { scenario })),
  users: () => unwrap<User[]>(api.get("/admin/users")),
  createUser: (body: Record<string, unknown>) => unwrap<User>(api.post("/admin/users", body)),
  updateUser: (id: string, body: Record<string, unknown>) => unwrap<User>(api.put(`/admin/users/${id}`, body)),
  thresholds: () => unwrap<Array<Record<string, unknown>>>(api.get("/admin/risk-thresholds")),
  updateThreshold: (category: string, body: Record<string, unknown>) => unwrap<unknown>(api.put(`/admin/risk-thresholds/${category}`, body)),
  audit: (page = 1) => unwrap<{ items: Array<Record<string, unknown>>; total: number }>(api.get("/admin/audit-logs", { params: { page } })),
  system: () => unwrap<Record<string, unknown>>(api.get("/admin/system")),
  weights: () => unwrap<Record<string, number>>(api.get("/admin/similarity-weights")),
  updateWeights: (body: Record<string, number>) => unwrap<unknown>(api.put("/admin/similarity-weights", body)),
  uploads: () => unwrap<Array<Record<string, unknown>>>(api.get("/admin/uploads")),
};

export function monitoringSocket(wellId: string, token: string, onMessage: (msg: LiveMessage) => void) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/monitoring/${encodeURIComponent(wellId)}?token=${encodeURIComponent(token)}`);
  socket.onmessage = (event) => onMessage(JSON.parse(event.data) as LiveMessage);
  const ping = window.setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) socket.send("ping");
  }, 15000);
  return () => {
    window.clearInterval(ping);
    socket.close();
  };
}
