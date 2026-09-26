import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../services/api";

interface DemoAccount {
  id: "admin" | "engineer" | "viewer";
  roleName: string;
  roleBadge: string;
  badgeColor: string;
  borderColor: string;
  activeRing: string;
  description: string;
  username: string;
  email: string;
  password: string;
  actionText: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    id: "admin",
    roleName: "Admin",
    roleBadge: "ADMIN",
    badgeColor: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    borderColor: "hover:border-amber-500/60",
    activeRing: "ring-2 ring-amber-500/80 border-amber-500/80 bg-amber-950/20",
    description: "Full system access",
    username: "admin",
    email: "admin@drilllens.local",
    password: "Admin123!",
    actionText: "Login as Admin",
  },
  {
    id: "engineer",
    roleName: "Drilling Engineer",
    roleBadge: "DRILLING ENGINEER",
    badgeColor: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    borderColor: "hover:border-blue-500/60",
    activeRing: "ring-2 ring-blue-500/80 border-blue-500/80 bg-blue-950/20",
    description: "Engineering intelligence and review access",
    username: "engineer",
    email: "engineer@drilllens.local",
    password: "Engineer123!",
    actionText: "Login as Drilling Engineer",
  },
  {
    id: "viewer",
    roleName: "Viewer",
    roleBadge: "VIEWER",
    badgeColor: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    borderColor: "hover:border-emerald-500/60",
    activeRing: "ring-2 ring-emerald-500/80 border-emerald-500/80 bg-emerald-950/20",
    description: "Read-only access",
    username: "viewer",
    email: "viewer@drilllens.local",
    password: "Viewer123!",
    actionText: "Login as Viewer",
  },
];

export function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [email, setEmail] = useState("");
  const [notice, setNotice] = useState("");
  const [token, setToken] = useState("");
  const [nextPassword, setNextPassword] = useState("");

  if (user) return <Navigate to="/dashboard" replace />;

  async function performLogin(targetUser: string, targetPass: string) {
    setError("");
    if (!targetUser.trim() || !targetPass) {
      setError("Login failed. Please verify the credentials or check the backend connection.");
      return;
    }
    setLoading(true);
    try {
      await login(targetUser.trim(), targetPass, remember);
    } catch {
      // Show user-friendly error without technical stack traces
      setError("Login failed. Please verify the credentials or check the backend connection.");
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    await performLogin(username, password);
  }

  function handleSelectAccount(account: DemoAccount, autoSubmit = false) {
    setUsername(account.username);
    setPassword(account.password);
    setSelectedRole(account.id);
    setError("");
    if (autoSubmit) {
      void performLogin(account.username, account.password);
    }
  }

  return (
    <div className="min-h-screen bg-ink text-slate-100 flex flex-col justify-between selection:bg-info selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-line bg-panel/70 backdrop-blur px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-gradient-to-br from-blue-600 via-sky-700 to-indigo-900 flex items-center justify-center shadow-lg shadow-blue-900/30 border border-blue-400/30">
            <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              DrillLens
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-info/20 text-sky-400 border border-info/30">
                MVP v1.0
              </span>
            </div>
            <div className="text-xs text-muted font-medium">Powered by eRTMAC-NWIS</div>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-3 text-xs text-muted font-mono">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-line">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            System Online
          </span>
          <span className="text-slate-400">SIH / Demo Mode</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col justify-center">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left Column: Login Card & Form */}
          <section className="lg:col-span-5 w-full">
            <div className="panel p-6 sm:p-8 shadow-2xl shadow-black/50 border-line bg-panel relative overflow-hidden">
              {/* Subtle accent glow */}
              <div className="absolute -top-24 -left-24 w-48 h-48 bg-info/10 rounded-full blur-3xl pointer-events-none" />

              <div className="mb-6">
                <h1 className="text-2xl font-bold tracking-tight text-white">Sign In</h1>
                <p className="text-sm text-muted mt-1">
                  Access the real-time drilling intelligence platform.
                </p>
              </div>

              {/* Login Error Notification */}
              {error && (
                <div
                  role="alert"
                  className="mb-5 p-3.5 rounded-md bg-crit/15 border border-crit/40 text-rose-300 text-sm flex items-start gap-2.5 animate-fadeIn"
                >
                  <svg className="w-5 h-5 text-crit shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span className="leading-snug">{error}</span>
                </div>
              )}

              <form onSubmit={onSubmit} className="space-y-4">
                {/* Username or Email Input */}
                <div>
                  <label htmlFor="login-username" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                    Username or Email
                  </label>
                  <div className="relative">
                    <input
                      id="login-username"
                      className="field pl-9 transition-colors focus:border-info"
                      autoComplete="username"
                      placeholder="e.g. admin or engineer@drilllens.local"
                      value={username}
                      onChange={(e) => {
                        setUsername(e.target.value);
                        setSelectedRole(null);
                      }}
                    />
                    <svg className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </div>
                </div>

                {/* Password Input */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label htmlFor="login-password" className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                      Password
                    </label>
                  </div>
                  <div className="relative flex gap-2">
                    <div className="relative flex-1">
                      <input
                        id="login-password"
                        className="field pl-9 pr-3 transition-colors focus:border-info font-mono"
                        type={showPassword ? "text" : "password"}
                        autoComplete="current-password"
                        placeholder="••••••••••••"
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          setSelectedRole(null);
                        }}
                      />
                      <svg className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </div>
                    <button
                      type="button"
                      className="btn shrink-0 text-xs px-3 transition-colors hover:text-white"
                      onClick={() => setShowPassword((prev) => !prev)}
                      title={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? "Hide" : "Show"}
                    </button>
                  </div>
                </div>

                {/* Remember Session & Forgot Password */}
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      className="rounded bg-ink border-line text-info focus:ring-info focus:ring-offset-ink"
                      checked={remember}
                      onChange={(e) => setRemember(e.target.checked)}
                    />
                    Remember session on this browser
                  </label>
                  <button
                    type="button"
                    className="text-xs text-info hover:text-sky-300 transition-colors"
                    onClick={() => setForgot((v) => !v)}
                  >
                    Forgot password?
                  </button>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  className="btn btn-primary w-full py-2.5 mt-2 text-sm font-semibold tracking-wide transition-all shadow-md active:scale-[0.99]"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-ink" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                      Authenticating…
                    </span>
                  ) : (
                    "Login"
                  )}
                </button>
              </form>

              {/* Forgot Password Drawer */}
              {forgot && (
                <div className="mt-5 p-4 rounded-lg bg-ink/70 border border-line space-y-3 animate-fadeIn">
                  <div className="text-xs font-semibold text-slate-200">Reset Credentials (Dev Mode)</div>
                  <label className="block text-xs text-muted">
                    Account email
                    <input
                      className="field mt-1 text-xs"
                      placeholder="e.g. admin@drilllens.local"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className="btn text-xs w-full"
                    onClick={async () => {
                      setNotice("");
                      try {
                        const response = await authApi.forgot(email);
                        setNotice(response.data.notice || response.message || "If the account exists, a reset token was issued.");
                        if (response.data.development_reset_token) setToken(response.data.development_reset_token);
                      } catch (err) {
                        setNotice(err instanceof Error ? err.message : "Request failed");
                      }
                    }}
                  >
                    Request reset token
                  </button>
                  {token && (
                    <>
                      <label className="block text-xs text-muted">
                        Reset token
                        <input className="field mt-1 text-xs font-mono" value={token} onChange={(e) => setToken(e.target.value)} />
                      </label>
                      <label className="block text-xs text-muted">
                        New password
                        <input className="field mt-1 text-xs font-mono" type="password" value={nextPassword} onChange={(e) => setNextPassword(e.target.value)} />
                      </label>
                      <button
                        type="button"
                        className="btn text-xs w-full"
                        onClick={async () => {
                          try {
                            const response = await authApi.reset(token, nextPassword);
                            setNotice(response.message || "Password updated.");
                          } catch (err) {
                            setNotice(err instanceof Error ? err.message : "Reset failed");
                          }
                        }}
                      >
                        Update password
                      </button>
                    </>
                  )}
                  {notice && <p className="text-xs text-info bg-info/10 p-2 rounded border border-info/20">{notice}</p>}
                </div>
              )}
            </div>
          </section>

          {/* Right Column: MVP Demo Accounts & System Overview */}
          <section className="lg:col-span-7 space-y-6">
            <div className="panel p-6 sm:p-7 border-line bg-panel/90 shadow-xl">
              
              {/* Header with MVP Label */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-line/60">
                <div>
                  <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                    MVP Demo Accounts
                    <span className="text-xs font-normal text-muted">| Quick Select</span>
                  </h2>
                  <p className="text-xs text-muted mt-0.5">
                    Click any card to load credentials or log in immediately for evaluation.
                  </p>
                </div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-info/10 border border-info/30 text-info text-xs font-mono shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-info" />
                  MVP Demo Credentials
                </div>
              </div>

              {/* Explanatory note */}
              <p className="text-xs text-slate-400 mt-3 leading-relaxed">
                This is intentional because the application is currently being demonstrated as an MVP. Each role provides access to different views, telemetry streams, and analytical permissions.
              </p>

              {/* Role Cards Grid */}
              <div className="mt-5 space-y-3.5">
                {DEMO_ACCOUNTS.map((account) => {
                  const isSelected = selectedRole === account.id;

                  return (
                    <div
                      key={account.id}
                      onClick={() => handleSelectAccount(account, false)}
                      className={`group relative p-4 rounded-lg border transition-all cursor-pointer bg-ink/60 ${
                        isSelected
                          ? account.activeRing
                          : `border-line ${account.borderColor} hover:bg-ink/90`
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center gap-2.5">
                            <span className={`text-[11px] font-bold font-mono px-2 py-0.5 rounded border uppercase tracking-wider ${account.badgeColor}`}>
                              {account.roleBadge}
                            </span>
                            <span className="text-sm font-semibold text-white group-hover:text-slate-100">
                              {account.roleName}
                            </span>
                            {isSelected && (
                              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/10 text-white border border-white/20">
                                Selected
                              </span>
                            )}
                          </div>
                          
                          <p className="text-xs text-slate-300 font-medium">
                            {account.description}
                          </p>

                          {/* Credentials Details */}
                          <div className="pt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted font-mono">
                            <span>
                              User: <strong className="text-slate-200">{account.username}</strong>
                            </span>
                            <span>
                              Email: <span className="text-slate-300">{account.email}</span>
                            </span>
                            <span>
                              Pass: <strong className="text-slate-200">{account.password}</strong>
                            </span>
                          </div>
                        </div>

                        {/* Action Button */}
                        <div className="sm:self-center shrink-0">
                          <button
                            type="button"
                            disabled={loading}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectAccount(account, true);
                            }}
                            className={`btn text-xs py-2 px-3.5 w-full sm:w-auto font-medium transition-all ${
                              isSelected
                                ? "bg-slate-100 text-ink border-white hover:bg-white shadow"
                                : "hover:border-slate-500 hover:text-white"
                            }`}
                          >
                            {account.actionText}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Bottom Notice */}
              <div className="mt-5 pt-3.5 border-t border-line/60 flex items-center justify-between text-xs text-muted">
                <span>Production deployments enforce RBAC &amp; MFA security policies.</span>
                <span className="font-mono text-[11px]">eRTMAC-NWIS Engine</span>
              </div>
            </div>

            {/* Industrial Context Card */}
            <div className="p-4 rounded-lg bg-panel/40 border border-line/50 text-xs text-muted space-y-2">
              <div className="font-semibold text-slate-300 flex items-center gap-2">
                <svg className="w-4 h-4 text-info" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                Enhanced Real-Time Monitoring &amp; Control Centre
              </div>
              <p className="leading-relaxed">
                Nearby Well Intelligence System correlates active drilling parameters with historical offsets, geological formations, trajectory logs, and real-time risk indicators. Decision support only. DrillLens does not control drilling equipment.
              </p>
            </div>
          </section>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-line bg-panel/40 px-6 py-3 text-center text-xs text-muted">
        <p>
          DrillLens &copy; {new Date().getFullYear()} – Real-Time Well Intelligence &amp; Drilling Risk Early Warning System.
        </p>
      </footer>
    </div>
  );
}
