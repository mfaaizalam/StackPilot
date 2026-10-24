import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import api from "../api/axios.js";
import { useBoards, KEYS } from "../api/queries.js";
import BoardModal from "../components/BoardModal.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import PendingInvitations from "../components/PendingInvitations.jsx";

// ── Icons (inline SVG, no extra deps) ──────────────────────────────────────
function IconPlus() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
    </svg>
  );
}
function IconEdit() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M9.5 2.5l2 2-7 7H2.5v-2l7-7z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
    </svg>
  );
}
function IconTrash() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 3.5h10M5.5 3.5V2.5h3v1M5.5 6v4.5M8.5 6v4.5M3 3.5l.5 8h7l.5-8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
function IconEmpty() {
  return (
    <svg className="text-line" width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="4" width="18" height="26" rx="3" stroke="currentColor" strokeWidth="2"/>
      <rect x="26" y="4" width="18" height="16" rx="3" stroke="currentColor" strokeWidth="2"/>
      <rect x="26" y="24" width="18" height="20" rx="3" stroke="currentColor" strokeWidth="2"/>
      <rect x="4" y="34" width="18" height="10" rx="3" stroke="currentColor" strokeWidth="2"/>
    </svg>
  );
}

// ── Project card ────────────────────────────────────────────────────────────
function ProjectCard({ project, onEdit, onDelete, onClick }) {
  const initials = project.name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || "")
    .join("");

  return (
    <div
      className="group relative bg-surface border border-line rounded-card p-5 hover:border-ink-muted/40 hover:shadow-sm transition cursor-pointer flex flex-col gap-3"
      onClick={() => onClick(project)}
    >
      {/* Action buttons */}
      <div
        className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={() => onEdit(project)}
          className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-ink hover:bg-surface-2 transition"
          title="Edit project"
        >
          <IconEdit />
        </button>
        <button
          onClick={() => onDelete(project)}
          className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-danger hover:bg-danger-soft transition"
          title="Delete project"
        >
          <IconTrash />
        </button>
      </div>

      {/* Avatar */}
      <div className="w-10 h-10 rounded-lg bg-brand text-brand-fg flex items-center justify-center text-sm font-semibold tracking-tight shrink-0">
        {initials || "P"}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-ink truncate pr-10">
          {project.name}
        </p>
        {project.description ? (
          <p className="mt-1 text-xs text-ink-muted line-clamp-2 leading-relaxed">
            {project.description}
          </p>
        ) : (
          <p className="mt-1 text-xs text-ink-muted/70 italic">No description</p>
        )}
      </div>
    </div>
  );
}

// ── Main Projects page ──────────────────────────────────────────────────────
export default function Boards() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Cached list: switching pages no longer refetches within the cache window.
  const {
    data: projects = [],
    isLoading: loading,
    error,
    refetch: fetchProjects,
  } = useBoards();

  const fetchError = error
    ? error?.response?.data?.detail || "Failed to load projects. Is the backend running?"
    : "";

  // Edit modal state (creating no longer uses the modal)
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState(null);

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // New-project state
  const [creating, setCreating] = useState(false);

  // Toast
  const [toast, setToast] = useState(null);

  // ── Cache helpers ─────────────────────────────────────────────────────────
  const syncAfterChange = (updater) => {
    queryClient.setQueryData(KEYS.boards, updater);
    queryClient.invalidateQueries({ queryKey: KEYS.dashboardSummary });
  };

  // ── Toast helper ──────────────────────────────────────────────────────────
  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // ── Handlers ──────────────────────────────────────────────────────────────
  // New project: create it right away, then let the user name it and describe
  // it on the Project Scope tab.
  const handleNewProject = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const { data } = await api.post("/boards/", { name: "Untitled project", description: "" });
      syncAfterChange((prev = []) => [data, ...prev]);
      navigate(`/boards/${data.id}/scope`);
    } catch (err) {
      showToast(err?.response?.data?.detail || "Could not create the project.", "error");
    } finally {
      setCreating(false);
    }
  };

  const handleEdit = async (form) => {
    const { data } = await api.put(`/boards/${editingProject.id}`, form);
    syncAfterChange((prev = []) => prev.map((p) => (p.id === data.id ? data : p)));
    queryClient.invalidateQueries({ queryKey: ["board", String(data.id)] });
    showToast("Project updated.");
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/boards/${deleteTarget.id}`);
      syncAfterChange((prev = []) => prev.filter((p) => p.id !== deleteTarget.id));
      showToast("Project deleted.");
      setDeleteTarget(null);
    } catch (err) {
      showToast(err?.response?.data?.detail || "Delete failed.", "error");
    } finally {
      setDeleteLoading(false);
    }
  };

  // Open project → Overview
  const handleOpenProject = (project) => {
    navigate(`/boards/${project.id}/overview`);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-canvas text-ink">
      {/* ── Header ── */}
      <header className="border-b border-line bg-surface sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center">
          <span className="text-lg font-semibold tracking-tight">Manage Projects</span>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Page heading */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            Projects
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            {projects.length > 0
              ? `${projects.length} project${projects.length === 1 ? "" : "s"}`
              : "Manage your projects"}
          </p>
        </div>

        <PendingInvitations />

        {/* ── Loading ── */}
        {loading && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 bg-surface border border-line rounded-card animate-pulse" />
            ))}
          </div>
        )}

        {/* ── Error ── */}
        {!loading && fetchError && (
          <div className="text-center py-20">
            <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-4 py-3 inline-block">
              {fetchError}
            </p>
            <div className="mt-4">
              <button
                onClick={() => fetchProjects()}
                className="text-sm text-ink-muted hover:text-ink underline underline-offset-2"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {/* ── Empty state ── */}
        {!loading && !fetchError && projects.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <IconEmpty />
            <p className="mt-5 text-base font-medium text-ink">No projects yet</p>
            <p className="mt-1.5 text-sm text-ink-muted max-w-xs">
              Create your first project, then describe it on the Project Scope tab.
            </p>
            <button
              onClick={handleNewProject}
              disabled={creating}
              className="mt-6 flex items-center gap-2 bg-brand text-brand-fg text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-brand-hover disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              <IconPlus />
              {creating ? "Creating…" : "Create a project"}
            </button>
          </div>
        )}

        {/* ── Project grid ── */}
        {!loading && !fetchError && projects.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onEdit={(p) => { setEditingProject(p); setModalOpen(true); }}
                onDelete={(p) => setDeleteTarget(p)}
                onClick={handleOpenProject}
              />
            ))}

            {/* "Add project" card */}
            <button
              onClick={handleNewProject}
              disabled={creating}
              className="h-full min-h-[9rem] flex flex-col items-center justify-center gap-2 border border-dashed border-ink-muted/40 rounded-card text-ink-muted/70 hover:border-ink-muted/60 hover:text-ink-muted hover:bg-surface disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              <IconPlus />
              <span className="text-sm font-medium">{creating ? "Creating…" : "New project"}</span>
            </button>
          </div>
        )}
      </main>

      {/* ── Modals ── */}
      <BoardModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditingProject(null); }}
        onSubmit={handleEdit}
        initial={editingProject}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        loading={deleteLoading}
        title={`Delete "${deleteTarget?.name}"?`}
        message="This will permanently delete the project. This action cannot be undone."
      />

      {/* ── Toast ── */}
      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 text-sm font-medium px-4 py-2.5 rounded-lg shadow-lg border transition-all ${
            toast.type === "error"
              ? "bg-danger-soft border-danger/20 text-danger"
              : "bg-surface border-line text-ink"
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}