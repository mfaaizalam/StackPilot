import { useEffect, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../api/axios.js";

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

const inputClass =
  "w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900/10";
const buttonClass =
  "inline-flex items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40";
const primaryButton = `${buttonClass} bg-neutral-950 text-white hover:bg-neutral-800`;
const secondaryButton = `${buttonClass} border border-neutral-200 text-neutral-700 hover:bg-neutral-50`;
const dangerButton = `${buttonClass} border border-red-100 text-red-600 hover:bg-red-50`;

function ErrorMessage({ children }) {
  if (!children) return null;
  return (
    <p className="mt-3 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
      {children}
    </p>
  );
}

function Section({ title, description, children }) {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-neutral-900">{title}</h2>
        {description && (
          <p className="mt-1 text-xs leading-relaxed text-neutral-500">
            {description}
          </p>
        )}
      </div>
      {children}
    </section>
  );
}

export default function BoardSettings() {
  const { boardId } = useParams();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [lookup, setLookup] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const {
    data: board,
    isLoading: boardLoading,
    error: boardError,
  } = useQuery({
    queryKey: ["board", boardId],
    queryFn: () => api.get(`/boards/${boardId}`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const {
    data: me,
    isLoading: roleLoading,
  } = useQuery({
    queryKey: ["board-role", boardId],
    queryFn: () => api.get(`/boards/${boardId}/me`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const role = me?.role || board?.my_role || "viewer";
  const isAdmin = role === "admin";

  const {
    data: members = [],
    isLoading: membersLoading,
    error: membersError,
  } = useQuery({
    queryKey: ["board-members", boardId],
    queryFn: () => api.get(`/boards/${boardId}/members`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const {
    data: invitations = [],
    isLoading: invitationsLoading,
    error: invitationsError,
  } = useQuery({
    queryKey: ["board-invitations", boardId],
    queryFn: () =>
      api.get(`/boards/${boardId}/invitations`).then((r) => r.data),
    enabled: Boolean(boardId) && isAdmin,
  });

  const {
    data: activity = [],
    isLoading: activityLoading,
    error: activityError,
  } = useQuery({
    queryKey: ["board-activity", boardId],
    queryFn: () =>
      api.get(`/boards/${boardId}/activity?limit=50`).then((r) => r.data),
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
    setNotice("");
  }, [email]);

  const showError = (e, fallback) =>
    e?.response?.data?.detail || fallback;

  const handleLookup = async () => {
    if (!email.trim()) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const { data } = await api.get(
        `/boards/${boardId}/members/lookup`,
        { params: { email: email.trim() } }
      );
      setLookup(data);
      if (data.registered) {
        setNotice(`Registered account found${data.name ? `: ${data.name}` : ""}.`);
      } else {
        setNotice("No account found for this email. The person must sign up first.");
      }
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
    setNotice("");
    try {
      await api.post(`/boards/${boardId}/invitations`, {
        email: email.trim().toLowerCase(),
        role: inviteRole,
      });
      setEmail("");
      setLookup(null);
      setNotice("Invitation saved. The invitation email will be sent if email is configured.");
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
    setNotice("");
    try {
      await api.patch(`/boards/${boardId}/members/${member.user_id}`, {
        role: nextRole,
      });
      setNotice(`Updated role for ${member.email}.`);
      refresh();
    } catch (e) {
      setError(showError(e, "Could not update this member's role."));
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveMember = async (member) => {
    if (!window.confirm(`Remove ${member.email} from this project?`)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.delete(`/boards/${boardId}/members/${member.user_id}`);
      setNotice(`${member.email} was removed.`);
      refresh();
    } catch (e) {
      setError(showError(e, "Could not remove this member."));
    } finally {
      setBusy(false);
    }
  };

  const handleRevokeInvite = async (invitation) => {
    if (!window.confirm(`Revoke the invitation for ${invitation.email}?`)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.delete(
        `/boards/${boardId}/invitations/${invitation.id}`
      );
      setNotice(`Invitation for ${invitation.email} was revoked.`);
      refresh();
    } catch (e) {
      setError(showError(e, "Could not revoke this invitation."));
    } finally {
      setBusy(false);
    }
  };

  if (boardLoading || roleLoading) {
    return <div className="p-8 text-sm text-neutral-500">Loading project settings…</div>;
  }

  if (boardError) {
    return (
      <div className="p-8">
        <p className="text-sm text-red-600">
          {showError(boardError, "Could not load this project.")}
        </p>
        <Link to="/boards" className="mt-3 inline-block text-sm underline">
          Back to projects
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            to={`/boards/${boardId}/kanban`}
            className="text-xs text-neutral-500 hover:text-neutral-900"
          >
            ← Back to board
          </Link>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900">
            Project settings
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            {board?.name || "Project"} · Your role: {roleLabel(role)}
          </p>
        </div>
        <span className="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600">
          {roleLabel(role)}
        </span>
      </div>

      {notice && (
        <p className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {notice}
        </p>
      )}
      <ErrorMessage>{error}</ErrorMessage>

      {isAdmin && (
        <Section
          title="Invite a member"
          description="Invite a registered StackPilot user by email. Invitations expire after seven days."
        >
          <form onSubmit={handleInvite} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px_auto_auto]">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="person@gmail.com"
                className={inputClass}
              />
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className={inputClass}
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
              <button
                type="submit"
                disabled={busy || !email.trim()}
                className={primaryButton}
              >
                {busy ? "Please wait…" : "Send invite"}
              </button>
            </div>
            {lookup && (
              <p className="text-xs text-neutral-500">
                {lookup.registered
                  ? `Account found${lookup.name ? ` for ${lookup.name}` : ""}.`
                  : "This email is not registered yet. The user must create an account before accepting."}
              </p>
            )}
          </form>
        </Section>
      )}

      <Section
        title={`Members${members.length ? ` (${members.length})` : ""}`}
        description="Project access is controlled by each member's role."
      >
        {membersLoading ? (
          <p className="text-sm text-neutral-500">Loading members…</p>
        ) : membersError ? (
          <p className="text-sm text-red-600">
            {showError(membersError, "Could not load members.")}
          </p>
        ) : members.length === 0 ? (
          <p className="text-sm text-neutral-500">No members found.</p>
        ) : (
          <div className="divide-y divide-neutral-100">
            {members.map((member) => (
              <div
                key={member.user_id}
                className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-neutral-900">
                    {member.name || member.email}
                    {member.is_owner && (
                      <span className="ml-2 text-xs font-normal text-neutral-400">Owner</span>
                    )}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-neutral-500">
                    {member.email}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {isAdmin && !member.is_owner ? (
                    <>
                      <select
                        value={member.role}
                        disabled={busy}
                        onChange={(e) => handleRoleChange(member, e.target.value)}
                        className="rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs text-neutral-700"
                        aria-label={`Role for ${member.email}`}
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value}>{r.label}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleRemoveMember(member)}
                        className={dangerButton}
                      >
                        Remove
                      </button>
                    </>
                  ) : (
                    <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs text-neutral-600">
                      {roleLabel(member.role)}
                    </span>
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
            <p className="text-sm text-neutral-500">Loading invitations…</p>
          ) : invitationsError ? (
            <p className="text-sm text-red-600">
              {showError(invitationsError, "Could not load invitations.")}
            </p>
          ) : invitations.length === 0 ? (
            <p className="text-sm text-neutral-500">No pending invitations.</p>
          ) : (
            <div className="divide-y divide-neutral-100">
              {invitations.map((inv) => (
                <div key={inv.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-neutral-900">{inv.email}</p>
                    <p className="mt-0.5 text-xs text-neutral-500">
                      {roleLabel(inv.role)} · Expires {new Date(inv.expires_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => handleRevokeInvite(inv)}
                    className={dangerButton}
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
          <p className="text-sm text-neutral-500">Loading activity…</p>
        ) : activityError ? (
          <p className="text-sm text-red-600">
            {showError(activityError, "Could not load activity.")}
          </p>
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
  );
}