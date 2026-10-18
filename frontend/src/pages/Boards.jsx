import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import api from "../api/axios.js";
import { useBoards, KEYS } from "../api/queries.js";
import BoardModal from "../components/BoardModal.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";

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
function IconBoard() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="7" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="11" y="2" width="7" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="11" y="10" width="7" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="2" y="14" width="7" height="4" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
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

// ── Board card ──────────────────────────────────────────────────────────────
function BoardCard({ board, onEdit, onDelete, onClick }) {
  const initials = board.name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || "")
    .join("");

  return (
    <div
      className="group relative bg-surface border border-line rounded-card p-5 hover:border-ink-muted/40 hover:shadow-sm transition cursor-pointer flex flex-col gap-3"
      onClick={() => onClick(board)}
    >
      {/* Action buttons */}
      <div
        className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={() => onEdit(board)}
          className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-ink hover:bg-surface-2 transition"
          title="Edit board"
        >
          <IconEdit />
        </button>
        <button
          onClick={() => onDelete(board)}
          className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-danger hover:bg-danger-soft transition"
          title="Delete board"
        >
          <IconTrash />
        </button>
      </div>

      {/* Avatar */}
      <div className="w-10 h-10 rounded-lg bg-brand text-brand-fg flex items-center justify-center text-sm font-semibold tracking-tight shrink-0">
        {initials || "B"}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-ink truncate pr-10">
          {board.name}
        </p>
        {board.description ? (
          <p className="mt-1 text-xs text-ink-muted line-clamp-2 leading-relaxed">
            {board.description}
          </p>
        ) : (
          <p className="mt-1 text-xs text-ink-muted/70 italic">No description</p>
        )}
      </div>
    </div>
  );
}

// ── Main Boards page ────────────────────────────────────────────────────────
export default function Boards() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = JSON.parse(localStorage.getItem("user") || "null");

  // Cached list: switching Home <-> Boards no longer refetches within the cache window.
  const {
    data: boards = [],
    isLoading: loading,
    error,
    refetch: fetchBoards,
  } = useBoards();

  const fetchError = error
    ? error?.response?.data?.detail || "Failed to load boards. Is the backend running?"
    : "";

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBoard, setEditingBoard] = useState(null); // null = create, object = edit

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Toast
  const [toast, setToast] = useState(null);

  // ── Cache helpers ─────────────────────────────────────────────────────────
  // Update the cached list immediately and mark the dashboard counts stale
  // so Home shows correct numbers next time it opens.
  const syncAfterChange = (updater) => {
    queryClient.setQueryData(KEYS.boards, updater);
    queryClient.invalidateQueries({ queryKey: KEYS.dashboardSummary });
  };

  // ── Toast helper ──────────────────────────────────────────────────────────
  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // ── CRUD handlers ─────────────────────────────────────────────────────────
  const handleCreate = async (form) => {
    const { data } = await api.post("/boards/", form);
    syncAfterChange((prev = []) => [data, ...prev]);
    showToast("Board created.");
  };

  const handleEdit = async (form) => {
    const { data } = await api.put(`/boards/${editingBoard.id}`, form);
    syncAfterChange((prev = []) => prev.map((b) => (b.id === data.id ? data : b)));
    showToast("Board updated.");
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/boards/${deleteTarget.id}`);
      syncAfterChange((prev = []) => prev.filter((b) => b.id !== deleteTarget.id));
      showToast("Board deleted.");
      setDeleteTarget(null);
    } catch (err) {
      showToast(err?.response?.data?.detail || "Delete failed.", "error");
    } finally {
      setDeleteLoading(false);
    }
  };

  // ── Open board → navigate to board detail ────────────────────────────────
  const handleOpenBoard = (board) => {
    navigate(`/boards/${board.id}`);
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    queryClient.clear(); // don't leak cached data to the next user on this browser
    navigate("/login");
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-canvas text-ink">
      {/* ── Header ── */}
      <header className="border-b border-line bg-surface sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold tracking-tight">
            <div className="w-7 h-7 rounded-md bg-brand text-brand-fg flex items-center justify-center font-bold text-sm">
              S
            </div>
            StackPilot
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            {/* Desktop Navigation */}
            <nav className="hidden sm:flex items-center gap-1">
              <button
                onClick={() => navigate("/dashboard")}
                className="text-sm px-3 py-1.5 rounded-md text-ink-muted hover:text-ink hover:bg-surface-2 transition"
              >
                Home
              </button>

              <button className="text-sm px-3 py-1.5 rounded-md bg-surface-2 text-ink font-medium">
                Boards
              </button>
            </nav>

            {/* Mobile Home Button */}
            <button
              onClick={() => navigate("/dashboard")}
              className="sm:hidden flex items-center gap-1 text-sm px-2 py-1.5 rounded-md text-ink-muted hover:text-ink hover:bg-surface-2 transition"
            >
              <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
                <path
                  d="M10 12L6 8l4-4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Home
            </button>

            {/* User */}
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-9 h-9 rounded-full bg-brand text-brand-fg flex items-center justify-center font-semibold text-sm">
                {user?.name?.charAt(0) || "U"}
              </div>

              <div className="hidden sm:block">
                <p className="text-sm font-medium leading-none">
                  {user?.name || "User"}
                </p>
                <p className="text-xs text-ink-muted mt-0.5">
                  {user?.email || ""}
                </p>
              </div>
            </div>

            {/* Sign out */}
            <button
              onClick={logout}
              className="text-sm px-2.5 sm:px-3.5 py-2 rounded-lg border border-line hover:bg-surface-2 transition"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Page heading */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink">
              Boards
            </h1>
            <p className="mt-1 text-sm text-ink-muted">
              {boards.length > 0
                ? `${boards.length} board${boards.length === 1 ? "" : "s"}`
                : "Manage your project boards"}
            </p>
          </div>

          <button
            onClick={() => { setEditingBoard(null); setModalOpen(true); }}
            className="flex items-center gap-2 bg-brand text-brand-fg text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-brand-hover transition"
          >
            <IconPlus />
            New board
          </button>
        </div>

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
                onClick={() => fetchBoards()}
                className="text-sm text-ink-muted hover:text-ink underline underline-offset-2"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {/* ── Empty state ── */}
        {!loading && !fetchError && boards.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <IconEmpty />
            <p className="mt-5 text-base font-medium text-ink">No boards yet</p>
            <p className="mt-1.5 text-sm text-ink-muted max-w-xs">
              Create your first board to start organising columns and tasks.
            </p>
            <button
              onClick={() => { setEditingBoard(null); setModalOpen(true); }}
              className="mt-6 flex items-center gap-2 bg-brand text-brand-fg text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-brand-hover transition"
            >
              <IconPlus />
              Create a board
            </button>
          </div>
        )}

        {/* ── Board grid ── */}
        {!loading && !fetchError && boards.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {boards.map((board) => (
              <BoardCard
                key={board.id}
                board={board}
                onEdit={(b) => { setEditingBoard(b); setModalOpen(true); }}
                onDelete={(b) => setDeleteTarget(b)}
                onClick={handleOpenBoard}
              />
            ))}

            {/* "Add board" card */}
            <button
              onClick={() => { setEditingBoard(null); setModalOpen(true); }}
              className="h-full min-h-[9rem] flex flex-col items-center justify-center gap-2 border border-dashed border-ink-muted/40 rounded-card text-ink-muted/70 hover:border-ink-muted/60 hover:text-ink-muted hover:bg-surface transition"
            >
              <IconPlus />
              <span className="text-sm font-medium">New board</span>
            </button>
          </div>
        )}
      </main>

      {/* ── Modals ── */}
      <BoardModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={editingBoard ? handleEdit : handleCreate}
        initial={editingBoard}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        loading={deleteLoading}
        title={`Delete "${deleteTarget?.name}"?`}
        message="This will permanently delete the board. This action cannot be undone."
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