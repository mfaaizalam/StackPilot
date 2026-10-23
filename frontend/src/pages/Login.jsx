import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "../api/axios.js";
import AuthShell from "../components/AuthShell.jsx";
import { safeNext, authQuery } from "../utils/safeNext.js";
import { DEMO_TOKEN } from "../demo/demoMode.js";
import demoData from "../demo/demoAccount.json";

export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next")); // e.g. /invite/<token>
  const [form, setForm] = useState({ email: params.get("email") || "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", form);
      if (data?.token) localStorage.setItem("token", data.token);
      if (data?.access_token) localStorage.setItem("token", data.access_token);
      if (data?.user) localStorage.setItem("user", JSON.stringify(data.user));
      navigate(next || "/dashboard", { replace: true });
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.response?.data?.detail ||
          (err?.response
            ? "Invalid email or password."
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
      title="Welcome back"
      subtitle="Sign in to continue to your StackPilot workspace."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link
            to={`/register${authQuery(next, params.get("email"))}`}
            className="text-neutral-900 font-medium hover:underline"
          >
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1.5">
            Email
          </label>
          <input
            type="email"
            name="email"
            required
            value={form.email}
            onChange={handleChange}
            placeholder="you@company.com"
            className="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm placeholder:text-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm font-medium text-neutral-700">
              Password
            </label>
          </div>
          <input
            type="password"
            name="password"
            required
            value={form.password}
            onChange={handleChange}
            placeholder="••••••••"
            className="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm placeholder:text-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition"
          />
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-neutral-900 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-neutral-800 disabled:opacity-60 disabled:cursor-not-allowed transition"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <div className="mt-5 pt-5 border-t border-neutral-100">
        <button
          type="button"
          onClick={enterDemo}
          className="w-full border border-neutral-300 text-neutral-900 rounded-lg py-2.5 text-sm font-medium hover:bg-neutral-50 transition"
        >
          View demo account
        </button>
        <p className="mt-2 text-xs text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
          The backend is temporarily offline due to a security vulnerability on our
          hosting provider. Demo mode shows read-only sample data stored in your browser.
        </p>
      </div>
    </AuthShell>
  );
}