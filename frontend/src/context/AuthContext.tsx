import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { clearToken, getToken, setToken } from "../api/client";
import { authApi } from "../services/api";
import type { User } from "../types";

export const MVP_ACCOUNTS: Record<string, { user: User; pass: string }> = {
  admin: {
    user: {
      id: "usr-admin-001",
      username: "admin",
      email: "admin@drilllens.local",
      full_name: "Avery Admin",
      role: "ADMIN",
      is_active: true,
      last_login: new Date().toISOString(),
    },
    pass: "Admin123!",
  },
  "admin@drilllens.local": {
    user: {
      id: "usr-admin-001",
      username: "admin",
      email: "admin@drilllens.local",
      full_name: "Avery Admin",
      role: "ADMIN",
      is_active: true,
      last_login: new Date().toISOString(),
    },
    pass: "Admin123!",
  },
  engineer: {
    user: {
      id: "usr-eng-002",
      username: "engineer",
      email: "engineer@drilllens.local",
      full_name: "Riley Engineer",
      role: "DRILLING_ENGINEER",
      is_active: true,
      last_login: new Date().toISOString(),
    },
    pass: "Engineer123!",
  },
  "engineer@drilllens.local": {
    user: {
      id: "usr-eng-002",
      username: "engineer",
      email: "engineer@drilllens.local",
      full_name: "Riley Engineer",
      role: "DRILLING_ENGINEER",
      is_active: true,
      last_login: new Date().toISOString(),
    },
    pass: "Engineer123!",
  },
  viewer: {
    user: {
      id: "usr-view-003",
      username: "viewer",
      email: "viewer@drilllens.local",
      full_name: "Casey Viewer",
      role: "VIEWER",
      is_active: true,
      last_login: new Date().toISOString(),
    },
    pass: "Viewer123!",
  },
  "viewer@drilllens.local": {
    user: {
      id: "usr-view-003",
      username: "viewer",
      email: "viewer@drilllens.local",
      full_name: "Casey Viewer",
      role: "VIEWER",
      is_active: true,
      last_login: new Date().toISOString(),
    },
    pass: "Viewer123!",
  },
};

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string, remember: boolean) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const token = getToken();
    if (!token) {
      setUser(null);
      return;
    }

    // If using a demo session, restore demo user
    if (token.startsWith("demo_")) {
      const saved = localStorage.getItem("drilllens_demo_user");
      if (saved) {
        try {
          setUser(JSON.parse(saved));
          return;
        } catch {
          // fallback
        }
      }
    }

    try {
      const response = await authApi.me();
      if (response?.data) {
        setUser(response.data);
        return;
      }
      throw new Error("Invalid session");
    } catch {
      const saved = localStorage.getItem("drilllens_demo_user");
      if (saved) {
        try {
          setUser(JSON.parse(saved));
          return;
        } catch {
          clearToken();
          setUser(null);
        }
      } else {
        clearToken();
        setUser(null);
      }
    }
  }

  useEffect(() => {
    refresh().catch(() => clearToken()).finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(() => ({
    user,
    loading,
    login: async (username, password, remember) => {
      const normalized = username.trim().toLowerCase();
      try {
        const response = await authApi.login(username, password, remember);
        if (response?.data?.access_token) {
          setToken(response.data.access_token, remember);
          setUser(response.data.user);
          localStorage.removeItem("drilllens_demo_user");
          return;
        }
        throw new Error("Invalid response from server");
      } catch (err) {
        // Fallback for MVP demo accounts when backend connection is unavailable
        const match = MVP_ACCOUNTS[normalized];
        if (match && match.pass === password) {
          const demoToken = `demo_${match.user.role.toLowerCase()}_token`;
          setToken(demoToken, remember);
          localStorage.setItem("drilllens_demo_user", JSON.stringify(match.user));
          setUser(match.user);
          return;
        }
        throw err;
      }
    },
    logout: async () => {
      try { await authApi.logout(); } catch { /* ignore */ }
      localStorage.removeItem("drilllens_demo_user");
      clearToken();
      setUser(null);
    },
    refresh,
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider is required");
  return ctx;
}
