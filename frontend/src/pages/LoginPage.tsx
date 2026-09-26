import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../services/api";

export function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [email, setEmail] = useState("");
  const [notice, setNotice] = useState("");
  const [token, setToken] = useState("");
  const [nextPassword, setNextPassword] = useState("");

  if (user) return <Navigate to="/dashboard" replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!username.trim() || !password) {
      setError("Enter a username or email and a password.");
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), password, remember);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <section className="hidden lg:flex flex-col justify-between p-12 border-r border-line bg-panel">
        <div>
          <div className="text-3xl font-semibold">DrillLens</div>
          <div className="text-muted mt-1">Powered by eRTMAC-NWIS</div>
          <p className="mt-8 max-w-md text-sm leading-6 text-slate-300">
            Connect the current drilling condition to nearby wells, historical events, similarity, risk indicators, and source evidence.
          </p>
          <ol className="mt-8 space-y-2 text-sm text-muted">
            {["Current well", "Live parameters", "Nearby wells", "Historical events", "Well similarity", "Risk analysis", "Evidence", "Engineering review"].map((step, index) => (
              <li key={step}>{index + 1}. {step}</li>
            ))}
          </ol>
        </div>
        <p className="text-xs text-muted max-w-md">
          Enhanced Real-Time Monitoring &amp; Control Centre – Nearby Well Intelligence System. Decision support only. DrillLens does not control drilling equipment.
        </p>
      </section>
      <section className="flex items-center justify-center p-6">
        <form className="w-full max-w-md" onSubmit={onSubmit}>
          <div className="lg:hidden mb-6">
            <div className="text-2xl font-semibold">DrillLens</div>
            <div className="text-sm text-muted">Powered by eRTMAC-NWIS</div>
          </div>
          <h1 className="text-xl font-semibold">Sign in</h1>
          <p className="text-sm text-muted mt-1">Use your engineering account.</p>
          <label className="block mt-6 text-sm">Username or email
            <input className="field mt-1" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label className="block mt-4 text-sm">Password
            <div className="flex gap-2 mt-1">
              <input className="field" type={show ? "text" : "password"} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" className="btn" onClick={() => setShow((v) => !v)}>{show ? "Hide" : "Show"}</button>
            </div>
          </label>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Remember session on this browser
          </label>
          {error && <div role="alert" className="mt-4 text-sm text-crit">{error}</div>}
          <button className="btn btn-primary w-full mt-6" disabled={loading}>{loading ? "Signing in…" : "Login"}</button>
          <button type="button" className="mt-4 text-sm text-info" onClick={() => setForgot((v) => !v)}>Forgot password</button>
          {forgot && (
            <div className="mt-4 panel p-3 space-y-2">
              <label className="block text-sm">Account email
                <input className="field mt-1" value={email} onChange={(e) => setEmail(e.target.value)} />
              </label>
              <button type="button" className="btn" onClick={async () => {
                setNotice("");
                try {
                  const response = await authApi.forgot(email);
                  setNotice(response.data.notice || response.message || "If the account exists, a reset token was issued.");
                  if (response.data.development_reset_token) setToken(response.data.development_reset_token);
                } catch (err) {
                  setNotice(err instanceof Error ? err.message : "Request failed");
                }
              }}>Request reset</button>
              <label className="block text-sm">Reset token
                <input className="field mt-1" value={token} onChange={(e) => setToken(e.target.value)} />
              </label>
              <label className="block text-sm">New password
                <input className="field mt-1" type="password" value={nextPassword} onChange={(e) => setNextPassword(e.target.value)} />
              </label>
              <button type="button" className="btn" onClick={async () => {
                try {
                  const response = await authApi.reset(token, nextPassword);
                  setNotice(response.message || "Password updated.");
                } catch (err) {
                  setNotice(err instanceof Error ? err.message : "Reset failed");
                }
              }}>Update password</button>
              {notice && <p className="text-xs text-muted">{notice}</p>}
            </div>
          )}
          <p className="mt-8 text-xs text-muted">Enhanced Real-Time Monitoring &amp; Control Centre – Nearby Well Intelligence System</p>
        </form>
      </section>
    </div>
  );
}
