import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios.js";
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
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="4" width="18" height="26" rx="3" stroke="#d4d4d4" strokeWidth="2"/>
      <rect x="26" y="4" width="18" height="16" rx="3" stroke="#d4d4d4" strokeWidth="2"/>
      <rect x="26" y="24" width="18" height="20" rx="3" stroke="#d4d4d4" strokeWidth="2"/>
      <rect x="4" y="34" width="18" height="10" rx="3" stroke="#d4d4d4" strokeWidth="2"/>
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
      className="group relative bg-white border border-neutral-200 rounded-xl p-5 hover:border-neutral-300 hover:shadow-sm transition cursor-pointer flex flex-col gap-3"
      onClick={() => onClick(board)}
    >
      {/* Action buttons */}
      <div
        className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={() => onEdit(board)}
          className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition"
          title="Edit board"
        >
          <IconEdit />
        </button>
        <button
          onClick={() => onDelete(board)}
          className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-400 hover:text-red-600 hover:bg-red-50 transition"
          title="Delete board"
        >
          <IconTrash />
        </button>
      </div>

      {/* Avatar */}
      <div className="w-10 h-10 rounded-lg bg-neutral-950 text-white flex items-center justify-center text-sm font-semibold tracking-tight shrink-0">
        {initials || "B"}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-neutral-900 truncate pr-10">
          {board.name}
        </p>
        {board.description ? (
          <p className="mt-1 text-xs text-neutral-500 line-clamp-2 leading-relaxed">
            {board.description}
          </p>
        ) : (
          <p className="mt-1 text-xs text-neutral-400 italic">No description</p>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-1.5 text-xs text-neutral-400">
        <IconBoard />
        <span>Board #{board.id}</span>
      </div>
    </div>
  );
}

// ── Main Boards page ────────────────────────────────────────────────────────
export default function Boards() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("user") || "null");

  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBoard, setEditingBoard] = useState(null); // null = create, object = edit

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Toast
  const [toast, setToast] = useState(null);

  // ── Data fetching ─────────────────────────────────────────────────────────
  const fetchBoards = useCallback(async () => {
    setLoading(true);
    setFetchError("");
    try {
      const { data } = await api.get("/boards/");
      setBoards(data);
    } catch (err) {
      setFetchError(
        err?.response?.data?.detail || "Failed to load boards. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchBoards(); }, [fetchBoards]);

  // ── Toast helper ──────────────────────────────────────────────────────────
  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // ── CRUD handlers ─────────────────────────────────────────────────────────
  const handleCreate = async (form) => {
    const { data } = await api.post("/boards/", form);
    setBoards((prev) => [data, ...prev]);
    showToast("Board created.");
  };

  const handleEdit = async (form) => {
    const { data } = await api.put(`/boards/${editingBoard.id}`, form);
    setBoards((prev) => prev.map((b) => (b.id === data.id ? data : b)));
    showToast("Board updated.");
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/boards/${deleteTarget.id}`);
      setBoards((prev) => prev.filter((b) => b.id !== deleteTarget.id));
      showToast("Board deleted.");
      setDeleteTarget(null);
    } catch (err) {
      showToast(err?.response?.data?.detail || "Delete failed.", "error");
    } finally {
      setDeleteLoading(false);
    }
  };

  // ── Open board → navigate to board detail (future page) ──────────────────
  const handleOpenBoard = (board) => {
    // Will navigate to /boards/:id when that page exists
    // For now, a no-op so clicking the card doesn't trigger edit/delete
    navigate(`/boards/${board.id}`);
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* ── Header ── */}
      <header className="border-b border-neutral-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold tracking-tight">
            <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center font-bold text-sm">
              S
            </div>
            StackPilot
          </div>

          <div className="flex items-center gap-4">
            <nav className="hidden sm:flex items-center gap-1">
              <button onClick={() => navigate("/dashboard")} className="text-sm px-3 py-1.5 rounded-md text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 transition">Home</button>
              <button className="text-sm px-3 py-1.5 rounded-md bg-neutral-100 text-neutral-900 font-medium">
                Boards
              </button>
            </nav>

            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-neutral-900 text-white flex items-center justify-center font-semibold text-sm">
                {user?.name?.charAt(0) || "U"}
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-medium leading-none">{user?.name || "User"}</p>
                <p className="text-xs text-neutral-500 mt-0.5">{user?.email || ""}</p>
              </div>
            </div>

            <button
              onClick={logout}
              className="text-sm px-3.5 py-2 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition"
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
            <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
              Boards
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              {boards.length > 0
                ? `${boards.length} board${boards.length === 1 ? "" : "s"}`
                : "Manage your project boards"}
            </p>
          </div>

          <button
            onClick={() => { setEditingBoard(null); setModalOpen(true); }}
            className="flex items-center gap-2 bg-neutral-950 text-white text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-neutral-800 transition"
          >
            <IconPlus />
            New board
          </button>
        </div>

        {/* ── Loading ── */}
        {loading && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 bg-white border border-neutral-200 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {/* ── Error ── */}
        {!loading && fetchError && (
          <div className="text-center py-20">
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3 inline-block">
              {fetchError}
            </p>
            <div className="mt-4">
              <button
                onClick={fetchBoards}
                className="text-sm text-neutral-600 hover:text-neutral-900 underline underline-offset-2"
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
            <p className="mt-5 text-base font-medium text-neutral-900">No boards yet</p>
            <p className="mt-1.5 text-sm text-neutral-500 max-w-xs">
              Create your first board to start organising columns and tasks.
            </p>
            <button
              onClick={() => { setEditingBoard(null); setModalOpen(true); }}
              className="mt-6 flex items-center gap-2 bg-neutral-950 text-white text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-neutral-800 transition"
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
              className="h-full min-h-[9rem] flex flex-col items-center justify-center gap-2 border border-dashed border-neutral-300 rounded-xl text-neutral-400 hover:border-neutral-400 hover:text-neutral-600 hover:bg-white transition"
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
              ? "bg-red-50 border-red-100 text-red-700"
              : "bg-white border-neutral-200 text-neutral-900"
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}