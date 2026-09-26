import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { clearToken, getToken, setToken } from "../api/client";
import { authApi } from "../services/api";
import type { User } from "../types";

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

    try {
      const response = await authApi.me();
      if (response?.data) {
        setUser(response.data);
        return;
      }
      throw new Error("Invalid session");
    } catch {
      clearToken();
      setUser(null);
    }
  }

  useEffect(() => {
    refresh().catch(() => clearToken()).finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(() => ({
    user,
    loading,
    login: async (username, password, remember) => {
      const response = await authApi.login(username, password, remember);
      if (response?.data?.access_token) {
        setToken(response.data.access_token, remember);
        setUser(response.data.user);
        return;
      }
      throw new Error("Invalid response from server");
    },
    logout: async () => {
      try { await authApi.logout(); } catch { /* ignore */ }
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
