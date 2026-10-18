import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "../api/axios.js";
import { queryClient } from "../api/queryClient.js";
import AuthShell from "../components/AuthShell.jsx";
import { authQuery } from "../utils/safeNext.js";

const roleLabel = (role) =>
  ({
    admin: "Admin",
    project_manager: "Project Manager",
    editor: "Editor",
    viewer: "Viewer",
  })[role] || role;

const primaryBtn =
  "w-full bg-neutral-900 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-neutral-800 disabled:opacity-60 disabled:cursor-not-allowed transition text-center";
const secondaryBtn =
  "w-full border border-neutral-200 bg-white text-neutral-700 rounded-lg py-2.5 text-sm font-medium hover:bg-neutral-50 disabled:opacity-60 disabled:cursor-not-allowed transition text-center";

export default function AcceptInvite() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const loggedIn = Boolean(localStorage.getItem("token"));
  const me = JSON.parse(localStorage.getItem("user") || "null");
  const next = `/invite/${token}`;

  const { data: inv, isLoading, error: loadError } = useQuery({
    queryKey: ["invite-preview", token],
    queryFn: () => api.get(`/invitations/token/${token}`).then((r) => r.data),
    retry: false,
  });

  const switchAccount = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("lastBoardId");
    queryClient.clear(); // don't leak the other account's cached data
    navigate(`/login${authQuery(next, inv?.email)}`);
  };

  const respond = async (action) => {
    setBusy(action);
    setError("");
    try {
      const { data } = await api.post(`/invitations/token/${token}/${action}`);
      queryClient.invalidateQueries({ queryKey: ["my-invitations"] });
      if (action === "accept") {
        navigate(`/boards/${data.board_id}/kanban`, { replace: true });
      } else {
        navigate("/boards", { replace: true });
      }
    } catch (e) {
      setError(e?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setBusy("");
    }
  };

  if (isLoading) {
    return (
      <AuthShell title="Loading invitation…" subtitle="One moment.">
        <div className="h-24 bg-white border border-neutral-200 rounded-xl animate-pulse" />
      </AuthShell>
    );
  }

  if (loadError || !inv) {
    return (
      <AuthShell
        title="Invitation not found"
        subtitle="This link is not valid. Ask the project admin to send a new invitation."
      >
        <Link to={loggedIn ? "/boards" : "/login"} className={primaryBtn + " block"}>
          {loggedIn ? "Go to my projects" : "Go to sign in"}
        </Link>
      </AuthShell>
    );
  }

  if (inv.status !== "pending") {
    const text =
      inv.status === "expired"
        ? "This invitation has expired. Ask the project admin to send a new one."
        : `This invitation was already ${inv.status}.`;
    return (
      <AuthShell title="Invitation unavailable" subtitle={text}>
        <Link to={loggedIn ? "/boards" : "/login"} className={primaryBtn + " block"}>
          {loggedIn ? "Go to my projects" : "Go to sign in"}
        </Link>
      </AuthShell>
    );
  }

  const wrongAccount =
    loggedIn && me?.email && me.email.toLowerCase() !== inv.email.toLowerCase();

  return (
    <AuthShell
      title={`Join “${inv.board_name || "a project"}”`}
      subtitle={`${inv.invited_by || "A teammate"} invited you as ${roleLabel(inv.role)}.`}
    >
      <div className="space-y-5">
        <div className="rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm">
          <p className="text-[11px] text-neutral-400 font-medium uppercase tracking-wide">
            Invitation sent to
          </p>
          <p className="mt-1 font-medium text-neutral-900 break-all">{inv.email}</p>
        </div>

        {!loggedIn ? (
          <div className="space-y-3">
            <p className="text-sm text-neutral-500">
              {inv.registered
                ? "Sign in with this email address to accept the invitation."
                : "Create a StackPilot account with this email address to accept the invitation."}
            </p>
            <Link
              to={`${inv.registered ? "/login" : "/register"}${authQuery(next, inv.email)}`}
              className={primaryBtn + " block"}
            >
              {inv.registered ? "Sign in to accept" : "Create account to accept"}
            </Link>
            <Link
              to={`${inv.registered ? "/register" : "/login"}${authQuery(next, inv.email)}`}
              className={secondaryBtn + " block"}
            >
              {inv.registered ? "Create a new account" : "I already have an account"}
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {wrongAccount && (
              <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                You are signed in as {me.email}, but this invitation is for {inv.email}.
              </p>
            )}
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <button
              type="button"
              disabled={Boolean(busy) || wrongAccount}
              onClick={() => respond("accept")}
              className={primaryBtn}
            >
              {busy === "accept" ? "Joining…" : "Accept invitation"}
            </button>
            <button
              type="button"
              disabled={Boolean(busy) || wrongAccount}
              onClick={() => respond("decline")}
              className={secondaryBtn}
            >
              {busy === "decline" ? "Declining…" : "Decline"}
            </button>
            <p className="text-center text-xs text-neutral-500">
              {me?.email ? `Signed in as ${me.email}. ` : ""}
              <button
                type="button"
                onClick={switchAccount}
                className="text-neutral-900 font-medium hover:underline"
              >
                Use a different account
              </button>
            </p>
          </div>
        )}
      </div>
    </AuthShell>
  );
}
