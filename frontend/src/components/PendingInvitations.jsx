import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../api/axios.js";

const roleLabel = (role) =>
  ({
    admin: "Admin",
    project_manager: "Project Manager",
    editor: "Editor",
    viewer: "Viewer",
  })[role] || role;

// Invitations addressed to the signed-in user's email. Shown on the Boards page so an
// invite can be accepted even if the email link is lost.
export default function PendingInvitations() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

  const { data: invites = [] } = useQuery({
    queryKey: ["my-invitations"],
    queryFn: () => api.get("/invitations/mine").then((r) => r.data),
  });

  if (invites.length === 0) return null;

  const respond = async (inv, action) => {
    setBusyId(inv.id);
    setError("");
    try {
      const { data } = await api.post(`/invitations/${inv.id}/${action}`);
      queryClient.invalidateQueries({ queryKey: ["my-invitations"] });
      if (action === "accept") navigate(`/boards/${data.board_id}/kanban`);
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not update this invitation.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="mb-8 rounded-2xl border border-line bg-surface p-5">
      <h2 className="text-sm font-semibold text-ink">
        Invitations for you ({invites.length})
      </h2>
      <p className="mt-1 text-xs text-ink-muted">
        You have been invited to join these projects.
      </p>
      {error && (
        <p className="mt-3 text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      <div className="mt-4 divide-y divide-neutral-100">
        {invites.map((inv) => (
          <div
            key={inv.id}
            className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink">
                {inv.board_name || "Project"}
              </p>
              <p className="mt-0.5 text-xs text-ink-muted">
                Join as {roleLabel(inv.role)} · Expires{" "}
                {new Date(inv.expires_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busyId === inv.id}
                onClick={() => respond(inv, "decline")}
                className="text-sm font-medium px-3.5 py-2 rounded-lg border border-line text-ink hover:bg-surface-2 disabled:opacity-40 transition"
              >
                Decline
              </button>
              <button
                type="button"
                disabled={busyId === inv.id}
                onClick={() => respond(inv, "accept")}
                className="text-sm font-medium px-3.5 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover disabled:opacity-40 transition"
              >
                Accept
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
