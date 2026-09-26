import type { Role } from "../types";

export const PERMISSIONS = {
  // Dashboard & Wells
  DASHBOARD_VIEW: "dashboard:view",
  WELLS_VIEW: "wells:view",
  WELLS_CREATE: "wells:create",
  WELLS_EDIT: "wells:edit",
  WELLS_DELETE: "wells:delete",

  // Drilling Data
  DRILLING_DATA_VIEW: "drilling_data:view",
  DRILLING_DATA_WRITE: "drilling_data:write",
  DRILLING_DATA_DELETE: "drilling_data:delete",

  // Historical Records
  HISTORICAL_RECORDS_VIEW: "historical_records:view",
  HISTORICAL_RECORDS_UPLOAD: "historical_records:upload",
  HISTORICAL_RECORDS_DELETE: "historical_records:delete",

  // Well Comparison & Risk
  COMPARISON_VIEW: "comparison:view",
  COMPARISON_ANALYZE: "comparison:analyze",
  RISK_VIEW: "risk:view",
  RISK_ANALYZE: "risk:analyze",

  // Alerts
  ALERTS_VIEW: "alerts:view",
  ALERTS_ACKNOWLEDGE: "alerts:acknowledge",
  ALERTS_MANAGE: "alerts:manage",

  // Evidence & Reviews
  EVIDENCE_VIEW: "evidence:view",
  EVIDENCE_SEARCH: "evidence:search",
  REVIEWS_VIEW: "reviews:view",
  REVIEWS_CREATE: "reviews:create",
  REVIEWS_EDIT: "reviews:edit",
  REVIEWS_DELETE: "reviews:delete",

  // AI & Reports
  AI_INSIGHTS_VIEW: "ai:view",
  AI_INSIGHTS_ASK: "ai:ask",
  REPORTS_VIEW: "reports:view",
  REPORTS_EXPORT: "reports:export",
  DATA_IMPORT: "data:import",

  // Administration
  USERS_MANAGE: "users:manage",
  ROLES_MANAGE: "roles:manage",
  SYSTEM_MANAGE: "system:manage",
  API_CONFIG_MANAGE: "api_config:manage",
  AUDIT_LOGS_VIEW: "audit_logs:view",
  PERMANENT_DELETE: "permanent:delete",
} as const;

export type PermissionKey = keyof typeof PERMISSIONS;
export type PermissionValue = (typeof PERMISSIONS)[PermissionKey];

export const ROLE_PERMISSIONS: Record<Role, Set<string>> = {
  ADMIN: new Set(Object.values(PERMISSIONS)),
  DRILLING_ENGINEER: new Set([
    PERMISSIONS.DASHBOARD_VIEW,
    PERMISSIONS.WELLS_VIEW,
    PERMISSIONS.WELLS_CREATE,
    PERMISSIONS.WELLS_EDIT,
    PERMISSIONS.DRILLING_DATA_VIEW,
    PERMISSIONS.DRILLING_DATA_WRITE,
    PERMISSIONS.HISTORICAL_RECORDS_VIEW,
    PERMISSIONS.HISTORICAL_RECORDS_UPLOAD,
    PERMISSIONS.COMPARISON_VIEW,
    PERMISSIONS.COMPARISON_ANALYZE,
    PERMISSIONS.RISK_VIEW,
    PERMISSIONS.RISK_ANALYZE,
    PERMISSIONS.ALERTS_VIEW,
    PERMISSIONS.ALERTS_ACKNOWLEDGE,
    PERMISSIONS.EVIDENCE_VIEW,
    PERMISSIONS.EVIDENCE_SEARCH,
    PERMISSIONS.REVIEWS_VIEW,
    PERMISSIONS.REVIEWS_CREATE,
    PERMISSIONS.REVIEWS_EDIT,
    PERMISSIONS.AI_INSIGHTS_VIEW,
    PERMISSIONS.AI_INSIGHTS_ASK,
    PERMISSIONS.REPORTS_VIEW,
    PERMISSIONS.REPORTS_EXPORT,
    PERMISSIONS.DATA_IMPORT,
    PERMISSIONS.AUDIT_LOGS_VIEW,
  ]),
  VIEWER: new Set([
    PERMISSIONS.DASHBOARD_VIEW,
    PERMISSIONS.WELLS_VIEW,
    PERMISSIONS.DRILLING_DATA_VIEW,
    PERMISSIONS.HISTORICAL_RECORDS_VIEW,
    PERMISSIONS.COMPARISON_VIEW,
    PERMISSIONS.RISK_VIEW,
    PERMISSIONS.ALERTS_VIEW,
    PERMISSIONS.EVIDENCE_VIEW,
    PERMISSIONS.EVIDENCE_SEARCH,
    PERMISSIONS.REVIEWS_VIEW,
    PERMISSIONS.AI_INSIGHTS_VIEW,
    PERMISSIONS.REPORTS_VIEW,
    PERMISSIONS.REPORTS_EXPORT,
  ]),
};

export function hasPermission(role?: Role | null, permission?: string): boolean {
  if (!role || !permission) return false;
  return ROLE_PERMISSIONS[role]?.has(permission) ?? false;
}

export function canWrite(role?: Role | null): boolean {
  return role === "ADMIN" || role === "DRILLING_ENGINEER";
}

export function canAdmin(role?: Role | null): boolean {
  return role === "ADMIN";
}

export function canAcknowledge(role?: Role | null): boolean {
  return hasPermission(role, PERMISSIONS.ALERTS_ACKNOWLEDGE);
}

export function canManageUsers(role?: Role | null): boolean {
  return hasPermission(role, PERMISSIONS.USERS_MANAGE);
}

export function isViewerOnly(role?: Role | null): boolean {
  return role === "VIEWER";
}

export function levelClass(level: string) {
  if (level === "CRITICAL") return "text-crit border-crit";
  if (level === "HIGH") return "text-high border-high";
  if (level === "MODERATE") return "text-warn border-warn";
  if (level === "LOW") return "text-ok border-ok";
  return "text-muted border-line";
}
