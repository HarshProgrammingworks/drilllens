import type { Role } from "../types";

export function canWrite(role?: Role | null) {
  return role === "ADMIN" || role === "DRILLING_ENGINEER";
}

export function canAdmin(role?: Role | null) {
  return role === "ADMIN";
}

export function levelClass(level: string) {
  if (level === "CRITICAL") return "text-crit border-crit";
  if (level === "HIGH") return "text-high border-high";
  if (level === "MODERATE") return "text-warn border-warn";
  if (level === "LOW") return "text-ok border-ok";
  return "text-muted border-line";
}
