import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../types";

export function RoleGuard({ allow, children }: { allow: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!allow.includes(user.role)) {
    return (
      <section className="panel p-6" role="alert">
        <h1 className="text-lg font-semibold">No permission</h1>
        <p className="mt-2 text-sm text-muted">Your role ({user.role}) cannot open this page. Ask an administrator if you need access.</p>
      </section>
    );
  }
  return <>{children}</>;
}
