import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "../api/axios.js";
import AuthShell from "../components/AuthShell.jsx";
import { safeNext, authQuery } from "../utils/safeNext.js";
import { DEMO_TOKEN } from "../demo/demoMode.js";
import demoData from "../demo/demoAccount.json";

export default function Register() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next")); // e.g. /invite/<token>
  const [form, setForm] = useState({
    name: "",
    email: params.get("email") || "",
    password: "",
    otp: "",
  });
  const [otpSent, setOtpSent] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const sendOtp = async () => {
    setError("");
    setInfo("");
    if (!form.email) return setError("Enter your email first to receive an OTP.");
    setSendingOtp(true);
    try {
      const { data } = await api.post("/auth/send-otp", { email: form.email });
      setOtpSent(true);
      if (data?.demo_mode) {
        setDemoMode(true);
        setForm((f) => ({ ...f, otp: "123456" })); // prefill for the demo
        setInfo("Demo mode: no email is sent. Code 123456 is filled in for you.");
      } else {
        setDemoMode(false);
        setInfo("OTP sent. Check your inbox.");
      }
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.response?.data?.detail ||
          (err?.response
            ? `OTP request failed. Status: ${err.response.status}`
            : "Cannot reach the server. The backend is currently offline.")
      );
    } finally {
      setSendingOtp(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      if (data?.token) localStorage.setItem("token", data.token);
      if (data?.access_token) localStorage.setItem("token", data.access_token);
      // Register does not return a token, so send them to sign in, keeping the invite link.
      if (data?.token || data?.access_token) navigate(next || "/dashboard");
      else navigate(`/login${authQuery(next, form.email)}`);
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.response?.data?.detail ||
          (err?.response
            ? "Registration failed."
            : "Cannot reach the server. The backend is currently offline.")
      );
    } finally {
      setLoading(false);
    }
  };

  const enterDemo = () => {
    localStorage.setItem("token", DEMO_TOKEN);
    localStorage.setItem("user", JSON.stringify(demoData.user));
    navigate("/dashboard", { replace: true });
  };

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start piloting your stack in under a minute."
      footer={
        <>
          Already have an account?{" "}
          <Link
            to={`/login${authQuery(next, params.get("email"))}`}
            className="text-ink font-medium hover:underline"
          >
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-ink mb-1.5">
            Full name
          </label>
          <input
            type="text"
            name="name"
            required
            value={form.name}
            onChange={handleChange}
            placeholder="Burhan Un Nadeem"
            className="w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-muted/70 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/10 transition"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-ink mb-1.5">
            Email
          </label>
          <div className="flex gap-2">
            <input
              type="email"
              name="email"
              required
              value={form.email}
              onChange={handleChange}
              placeholder="you@company.com"
              className="flex-1 rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-muted/70 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/10 transition"
            />
            <button
              type="button"
              onClick={sendOtp}
              disabled={sendingOtp}
              className="px-3.5 py-2.5 text-sm font-medium rounded-lg border border-line bg-surface hover:bg-surface-2 disabled:opacity-60 transition whitespace-nowrap"
            >
              {sendingOtp ? "Sending…" : otpSent ? "Resend" : "Send OTP"}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-ink mb-1.5">
            Password
          </label>
          <input
            type="password"
            name="password"
            required
            minLength={8}
            value={form.password}
            onChange={handleChange}
            placeholder="At least 8 characters"
            className="w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-muted/70 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/10 transition"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-ink mb-1.5">
            OTP
          </label>
          <input
            type="text"
            name="otp"
            required
            inputMode="numeric"
            value={form.otp}
            onChange={handleChange}
            placeholder="6-digit code"
            className="w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm tracking-widest placeholder:text-ink-muted/70 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/10 transition"
          />
          {demoMode && (
            <p className="mt-1.5 text-xs text-warning">
              Demo mode is on. Use code <strong>123456</strong>.
            </p>
          )}
        </div>

        {error && (
          <div className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
        {info && !error && (
          <div className="text-sm text-success bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
            {info}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-brand text-brand-fg rounded-lg py-2.5 text-sm font-medium hover:bg-brand-hover disabled:opacity-60 disabled:cursor-not-allowed transition"
        >
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>

      <div className="mt-5 pt-5 border-t border-line">
        <button
          type="button"
          onClick={enterDemo}
          className="w-full border border-line text-ink rounded-lg py-2.5 text-sm font-medium hover:bg-surface-2 transition"
        >
          View demo account
        </button>
        <p className="mt-2 text-xs text-warning bg-warning-soft border border-warning/30 rounded-lg px-3 py-2">
          The backend is temporarily offline due to a security vulnerability on Railway. Demo mode shows read-only sample data stored in your browser.
        </p>
      </div>
    </AuthShell>
  );
}