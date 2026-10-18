import { useEffect, useRef, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../api/axios.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";

const ROLES = [
  { value: "viewer", label: "Viewer" },
  { value: "editor", label: "Editor" },
  { value: "project_manager", label: "Project Manager" },
];

const roleLabel = (role) =>
  ({
    admin: "Admin",
    project_manager: "Project Manager",
    editor: "Editor",
    viewer: "Viewer",
  })[role] || role;

// Same input / button / pill styles as the Login, Boards and SRS pages.
const inputClass =
  "w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm placeholder:text-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition";
const primaryButton =
  "inline-flex items-center justify-center bg-neutral-950 text-white text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40 transition";
const secondaryButton =
  "inline-flex items-center justify-center border border-neutral-200 bg-white text-neutral-700 text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40 transition";
const dangerGhost =
  "text-xs font-medium text-red-500 hover:text-red-700 px-2.5 py-1.5 rounded-md hover:bg-red-50 disabled:opacity-40 transition";
const pillClass =
  "text-xs font-medium text-neutral-500 bg-neutral-100 border border-neutral-200 rounded-full px-2.5 py-1";

function ErrorMessage({ children }) {
  if (!children) return null;
  return (
    <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
      {children}
    </p>
  );
}

function Section({ title, description, children }) {
  return (
    <section className="bg-white border border-neutral-200 rounded-2xl p-5 sm:p-6">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-neutral-900">{title}</h2>
        {description && (
          <p className="mt-1 text-xs leading-relaxed text-neutral-500">{description}</p>
        )}
      </div>
      {children}
    </section>
  );
}

function Avatar({ name }) {
  return (
    <div className="w-9 h-9 rounded-full bg-neutral-900 text-white flex items-center justify-center font-semibold text-sm shrink-0">
      {(name || "?").charAt(0).toUpperCase()}
    </div>
  );
}

function Skeleton({ className = "h-16" }) {
  return <div className={`bg-neutral-50 border border-neutral-100 rounded-xl animate-pulse ${className}`} />;
}

export default function BoardSettings() {
  const { boardId } = useParams();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [lookup, setLookup] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [confirm, setConfirm] = useState(null); // { kind: "member" | "invite", target }
  const toastTimer = useRef(null);

  const showToast = (msg) => {
    setToast(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  };
  useEffect(() => () => clearTimeout(toastTimer.current), []);

  const { data: board, isLoading: boardLoading, error: boardError } = useQuery({
    queryKey: ["board", boardId],
    queryFn: () => api.get(`/boards/${boardId}`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const { data: me, isLoading: roleLoading } = useQuery({
    queryKey: ["board-role", boardId],
    queryFn: () => api.get(`/boards/${boardId}/me`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const role = me?.role || board?.my_role || "viewer";
  const isAdmin = role === "admin";

  const { data: members = [], isLoading: membersLoading, error: membersError } = useQuery({
    queryKey: ["board-members", boardId],
    queryFn: () => api.get(`/boards/${boardId}/members`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const { data: invitations = [], isLoading: invitationsLoading, error: invitationsError } = useQuery({
    queryKey: ["board-invitations", boardId],
    queryFn: () => api.get(`/boards/${boardId}/invitations`).then((r) => r.data),
    enabled: Boolean(boardId) && isAdmin,
  });

  const { data: activity = [], isLoading: activityLoading, error: activityError } = useQuery({
    queryKey: ["board-activity", boardId],
    queryFn: () => api.get(`/boards/${boardId}/activity?limit=50`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["board", boardId] });
    queryClient.invalidateQueries({ queryKey: ["board-role", boardId] });
    queryClient.invalidateQueries({ queryKey: ["board-members", boardId] });
    queryClient.invalidateQueries({ queryKey: ["board-invitations", boardId] });
    queryClient.invalidateQueries({ queryKey: ["board-activity", boardId] });
    queryClient.invalidateQueries({ queryKey: ["boards"] });
  }, [queryClient, boardId]);

  useEffect(() => {
    setLookup(null);
    setError("");
  }, [email]);

  const showError = (e, fallback) => e?.response?.data?.detail || fallback;

  const handleLookup = async () => {
    if (!email.trim()) return;
    setBusy(true);
    setError("");
    try {
      const { data } = await api.get(`/boards/${boardId}/members/lookup`, {
        params: { email: email.trim() },
      });
      setLookup(data);
    } catch (e) {
      setError(showError(e, "Could not look up this email."));
    } finally {
      setBusy(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    const target = email.trim().toLowerCase();
    try {
      await api.post(`/boards/${boardId}/invitations`, { email: target, role: inviteRole });
      setEmail("");
      setLookup(null);
      showToast(`Invitation sent to ${target}.`);
      refresh();
    } catch (e) {
      setError(showError(e, "Could not send the invitation."));
    } finally {
      setBusy(false);
    }
  };

  const handleRoleChange = async (member, nextRole) => {
    setBusy(true);
    setError("");
    try {
      await api.patch(`/boards/${boardId}/members/${member.user_id}`, { role: nextRole });
      showToast(`Updated role for ${member.email}.`);
      refresh();
    } catch (e) {
      setError(showError(e, "Could not update this member's role."));
    } finally {
      setBusy(false);
    }
  };

  const runConfirmed = async () => {
    if (!confirm) return;
    const { kind, target } = confirm;
    setBusy(true);
    setError("");
    try {
      if (kind === "member") {
        await api.delete(`/boards/${boardId}/members/${target.user_id}`);
        showToast(`${target.email} was removed.`);
      } else {
        await api.delete(`/boards/${boardId}/invitations/${target.id}`);
        showToast(`Invitation for ${target.email} was revoked.`);
      }
      refresh();
    } catch (e) {
      setError(showError(e, kind === "member" ? "Could not remove this member." : "Could not revoke this invitation."));
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };

  if (boardLoading || roleLoading) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <div className="border-b border-neutral-200 bg-white h-14" />
        <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
          <Skeleton className="h-40" />
          <Skeleton className="h-56" />
        </div>
      </div>
    );
  }

  if (boardError) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <div className="bg-white border border-dashed border-neutral-300 rounded-2xl px-6 py-14 text-center">
            <p className="text-base font-medium text-neutral-900">Could not load this project</p>
            <p className="mt-1.5 text-sm text-neutral-500">
              {showError(boardError, "It may have been deleted, or you may no longer have access.")}
            </p>
            <Link to="/boards" className={`${primaryButton} mt-5`}>
              Back to projects
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Page toolbar (same pattern as Diagrams / Costing) */}
      <div className="border-b border-neutral-200 bg-white sticky top-0 z-10 print:hidden">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between gap-3">
          <h1 className="text-sm font-semibold text-neutral-900 truncate">
            Settings
            {board?.name && <span className="font-normal text-neutral-400"> · {board.name}</span>}
          </h1>
          <span className={`${pillClass} shrink-0`}>Your role: {roleLabel(role)}</span>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {isAdmin && (
          <Section
            title="Invite a member"
            description="They get an email with a link to accept. If they don't have an account yet, they'll be asked to create one with the invited email. Invitations expire after seven days."
          >
            <form onSubmit={handleInvite} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px_auto_auto]">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="person@company.com"
                  className={inputClass}
                />
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className={inputClass}
                  aria-label="Role"
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleLookup}
                  disabled={busy || !email.trim()}
                  className={secondaryButton}
                >
                  Check email
                </button>
                <button type="submit" disabled={busy || !email.trim()} className={primaryButton}>
                  {busy ? "Please wait…" : "Send invite"}
                </button>
              </div>
              {lookup && (
                <p className="text-xs text-neutral-500">
                  {lookup.registered
                    ? `Registered account found${lookup.name ? `: ${lookup.name}` : ""}.`
                    : "No account yet. They can still accept the invitation after signing up with this email."}
                </p>
              )}
              <ErrorMessage>{error}</ErrorMessage>
            </form>
          </Section>
        )}

        {!isAdmin && error && <ErrorMessage>{error}</ErrorMessage>}

        <Section
          title={`Members${members.length ? ` (${members.length})` : ""}`}
          description="Project access is controlled by each member's role."
        >
          {membersLoading ? (
            <div className="space-y-3"><Skeleton /><Skeleton /></div>
          ) : membersError ? (
            <ErrorMessage>{showError(membersError, "Could not load members.")}</ErrorMessage>
          ) : members.length === 0 ? (
            <p className="text-sm text-neutral-500">No members found.</p>
          ) : (
            <div className="divide-y divide-neutral-100">
              {members.map((member) => (
                <div
                  key={member.user_id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Avatar name={member.name || member.email} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-neutral-900">
                        {member.name || member.email}
                        {member.is_owner && (
                          <span className="ml-2 text-[11px] font-medium text-neutral-500 bg-neutral-100 border border-neutral-200 rounded-full px-2 py-0.5">
                            Owner
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-neutral-500">{member.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isAdmin && !member.is_owner ? (
                      <>
                        <select
                          value={member.role}
                          disabled={busy}
                          onChange={(e) => handleRoleChange(member, e.target.value)}
                          className="rounded-lg border border-neutral-200 bg-white px-2.5 py-1.5 text-xs text-neutral-700 focus:outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition"
                          aria-label={`Role for ${member.email}`}
                        >
                          {ROLES.map((r) => (
                            <option key={r.value} value={r.value}>{r.label}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => setConfirm({ kind: "member", target: member })}
                          className={dangerGhost}
                        >
                          Remove
                        </button>
                      </>
                    ) : (
                      <span className={pillClass}>{roleLabel(member.role)}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        {isAdmin && (
          <Section title="Pending invitations" description="Invitations waiting to be accepted.">
            {invitationsLoading ? (
              <Skeleton />
            ) : invitationsError ? (
              <ErrorMessage>{showError(invitationsError, "Could not load invitations.")}</ErrorMessage>
            ) : invitations.length === 0 ? (
              <p className="text-sm text-neutral-500">No pending invitations.</p>
            ) : (
              <div className="divide-y divide-neutral-100">
                {invitations.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Avatar name={inv.email} />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-neutral-900">{inv.email}</p>
                        <p className="mt-0.5 text-xs text-neutral-500">
                          {roleLabel(inv.role)} · Expires {new Date(inv.expires_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => setConfirm({ kind: "invite", target: inv })}
                      className={dangerGhost}
                    >
                      Revoke
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Section>
        )}

        <Section title="Recent activity" description="Recent actions recorded for this project.">
          {activityLoading ? (
            <Skeleton />
          ) : activityError ? (
            <ErrorMessage>{showError(activityError, "Could not load activity.")}</ErrorMessage>
          ) : activity.length === 0 ? (
            <p className="text-sm text-neutral-500">No activity recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {activity.map((item) => (
                <div key={item.id} className="flex gap-3">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-neutral-300" />
                  <div className="min-w-0">
                    <p className="text-sm text-neutral-800">{item.summary}</p>
                    <p className="mt-0.5 text-xs text-neutral-400">
                      {item.user_name || "A member"} · {new Date(item.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>

      <ConfirmDialog
        open={Boolean(confirm)}
        onClose={() => setConfirm(null)}
        onConfirm={runConfirmed}
        loading={busy}
        title={confirm?.kind === "member" ? "Remove member?" : "Revoke invitation?"}
        message={
          confirm?.kind === "member"
            ? `${confirm?.target?.email} will lose access to this project.`
            : `The invitation link for ${confirm?.target?.email} will stop working.`
        }
        confirmLabel={confirm?.kind === "member" ? "Remove" : "Revoke"}
        loadingLabel="Working…"
      />

      {toast && (
        <div className="fixed bottom-5 right-5 z-50 text-sm font-medium px-4 py-2.5 rounded-lg shadow-lg border bg-white border-neutral-200 text-neutral-900">
          {toast}
        </div>
      )}
    </div>
  );
}
