import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/axios.js";
import ColumnModal from "../components/ColumnModal.jsx";
import TaskModal from "../components/TaskModal.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import ChatWidget from "../components/ChatWidget.jsx";

// ── Icons ────────────────────────────────────────────────────────────────────
function IconPlus({ size = 14 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>;
}
function IconEdit() {
  return <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M9.5 2.5l2 2-7 7H2.5v-2l7-7z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>;
}
function IconTrash() {
  return <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M2 3.5h10M5.5 3.5V2.5h3v1M5.5 6v4.5M8.5 6v4.5M3 3.5l.5 8h7l.5-8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function IconBack() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function IconDots() {
  return <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="3" r="1" fill="currentColor"/><circle cx="7" cy="7" r="1" fill="currentColor"/><circle cx="7" cy="11" r="1" fill="currentColor"/></svg>;
}
function IconClose() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>;
}
function IconGrip() {
  return <svg width="10" height="14" viewBox="0 0 10 14" fill="none"><circle cx="3" cy="3" r="1.2" fill="currentColor"/><circle cx="7" cy="3" r="1.2" fill="currentColor"/><circle cx="3" cy="7" r="1.2" fill="currentColor"/><circle cx="7" cy="7" r="1.2" fill="currentColor"/><circle cx="3" cy="11" r="1.2" fill="currentColor"/><circle cx="7" cy="11" r="1.2" fill="currentColor"/></svg>;
}
function IconAnalyze({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M2.5 13.5V9M6.5 13.5V5M10.5 13.5V7M14.5 13.5V2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

// ── Priority badge ───────────────────────────────────────────────────────────
const PRIORITY_STYLES = {
  high:   "bg-red-50 text-red-600 border-red-100",
  medium: "bg-amber-50 text-amber-600 border-amber-100",
  low:    "bg-neutral-100 text-neutral-500 border-neutral-200",
};
function PriorityBadge({ priority }) {
  const p = (priority || "low").toLowerCase();
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${PRIORITY_STYLES[p] || PRIORITY_STYLES.low}`}>
      {p.charAt(0).toUpperCase() + p.slice(1)}
    </span>
  );
}

// ── Task Detail slide-over panel ─────────────────────────────────────────────
function TaskDetail({ task, columns, onClose, onEdit, onDelete }) {
  if (!task) return null;
  const col = columns.find(c => c.id === task.column_id);
  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-30 bg-neutral-950/20 backdrop-blur-[2px]" onClick={onClose} />
      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 z-40 w-full max-w-sm bg-white border-l border-neutral-200 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
          <span className="text-xs text-neutral-400 font-medium uppercase tracking-wide">Task #{task.id}</span>
          <div className="flex items-center gap-1">
            <button onClick={() => { onClose(); onEdit(task); }} className="flex items-center gap-1.5 text-xs text-neutral-600 hover:text-neutral-900 px-2.5 py-1.5 rounded-md hover:bg-neutral-100 transition font-medium">
              <IconEdit /> Edit
            </button>
            <button onClick={() => { onClose(); onDelete(task); }} className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 px-2.5 py-1.5 rounded-md hover:bg-red-50 transition font-medium">
              <IconTrash /> Delete
            </button>
            <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition ml-1">
              <IconClose />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          <h2 className="text-lg font-semibold text-neutral-900 leading-snug">{task.title}</h2>

          {task.description ? (
            <p className="text-sm text-neutral-600 leading-relaxed whitespace-pre-wrap">{task.description}</p>
          ) : (
            <p className="text-sm text-neutral-400 italic">No description provided.</p>
          )}

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="bg-neutral-50 rounded-xl p-3 border border-neutral-100">
              <p className="text-[11px] text-neutral-400 font-medium uppercase tracking-wide mb-1.5">Priority</p>
              <PriorityBadge priority={task.priority} />
            </div>
            <div className="bg-neutral-50 rounded-xl p-3 border border-neutral-100">
              <p className="text-[11px] text-neutral-400 font-medium uppercase tracking-wide mb-1.5">Column</p>
              <p className="text-sm font-medium text-neutral-900">{col?.name || "—"}</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Task card (with drag support) ────────────────────────────────────────────
function TaskCard({ task, onView, onEdit, onDelete, onDragStart, onDragEnd }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const isDraft = !!task.__draft;

  const handleDragStart = (e) => {
    if (isDraft) return;
    setDragging(true);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("taskId", String(task.id));
    onDragStart?.(task);
  };
  const handleDragEnd = () => {
    setDragging(false);
    onDragEnd?.();
  };

  return (
    <div
      draggable={!isDraft}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onClick={() => { if (isDraft) return; if (!menuOpen) onView(task); }}
      className={`group relative bg-white border rounded-xl p-4 transition cursor-pointer select-none ${
        isDraft
          ? "border-dashed border-neutral-300 bg-neutral-50/70 hover:border-neutral-400"
          : `hover:border-neutral-300 hover:shadow-sm ${dragging ? "opacity-40 scale-95 border-neutral-300" : "border-neutral-200"}`
      }`}
    >
      {/* Drag grip — visible on hover, hidden for drafts */}
      {!isDraft && (
        <div className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-300 opacity-0 group-hover:opacity-100 transition cursor-grab active:cursor-grabbing">
          <IconGrip />
        </div>
      )}

      {/* Action menu — hidden for drafts, nothing to edit/delete until saved */}
      {!isDraft && (
        <div className="absolute top-3 right-3" onClick={e => e.stopPropagation()}>
          <button
            onClick={() => setMenuOpen(v => !v)}
            className="w-6 h-6 flex items-center justify-center rounded-md text-neutral-300 hover:text-neutral-600 hover:bg-neutral-100 opacity-0 group-hover:opacity-100 transition"
          >
            <IconDots />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-7 z-20 w-32 bg-white border border-neutral-200 rounded-lg shadow-lg py-1 text-sm">
                <button onClick={() => { setMenuOpen(false); onEdit(task); }} className="w-full flex items-center gap-2 px-3 py-2 text-neutral-700 hover:bg-neutral-50 transition">
                  <IconEdit /> Edit
                </button>
                <button onClick={() => { setMenuOpen(false); onDelete(task); }} className="w-full flex items-center gap-2 px-3 py-2 text-red-600 hover:bg-red-50 transition">
                  <IconTrash /> Delete
                </button>
              </div>
            </>
          )}
        </div>
      )}

      <p className={`text-sm font-medium pr-6 pl-4 leading-snug ${isDraft ? "text-neutral-600" : "text-neutral-900"}`}>{task.title}</p>
      {task.description && (
        <p className="mt-1.5 text-xs text-neutral-500 line-clamp-2 leading-relaxed pl-4">{task.description}</p>
      )}
      <div className="mt-3 flex items-center gap-2 pl-4">
        <PriorityBadge priority={task.priority} />
        {isDraft ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border bg-neutral-100 text-neutral-500 border-neutral-200">
            Draft · unsaved
          </span>
        ) : (
          <span className="text-[11px] text-neutral-400">#{task.id}</span>
        )}
      </div>
    </div>
  );
}

// ── Column panel (with drop zone) ────────────────────────────────────────────
function ColumnPanel({ column, tasks, onAddTask, onEditColumn, onDeleteColumn, onViewTask, onEditTask, onDeleteTask, onDropTask, draggedTask }) {
  const [dragOver, setDragOver] = useState(false);
  const dragCounter = useRef(0);

  const handleDragEnter = (e) => {
    e.preventDefault();
    dragCounter.current++;
    if (draggedTask && draggedTask.column_id !== column.id) setDragOver(true);
  };
  const handleDragLeave = () => {
    dragCounter.current--;
    if (dragCounter.current === 0) setDragOver(false);
  };
  const handleDragOver = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; };
  const handleDrop = (e) => {
    e.preventDefault();
    dragCounter.current = 0;
    setDragOver(false);
    const taskId = Number(e.dataTransfer.getData("taskId"));
    if (taskId && draggedTask?.column_id !== column.id) onDropTask(taskId, column.id);
  };

  return (
    <div
      className={`flex flex-col w-72 shrink-0 rounded-xl transition-all duration-150 ${dragOver ? "ring-2 ring-neutral-900 bg-neutral-100" : ""}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Column header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-neutral-900">{column.name}</span>
          <span className="text-xs text-neutral-400 bg-neutral-100 px-1.5 py-0.5 rounded-full font-medium">{tasks.length}</span>
        </div>
        <div className="flex items-center gap-0.5">
          <button onClick={() => onAddTask(column.id)} title="Add task" className="w-6 h-6 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition"><IconPlus size={13}/></button>
          <button onClick={() => onEditColumn(column)} title="Rename" className="w-6 h-6 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition"><IconEdit /></button>
          <button onClick={() => onDeleteColumn(column)} title="Delete" className="w-6 h-6 flex items-center justify-center rounded-md text-neutral-400 hover:text-red-600 hover:bg-red-50 transition"><IconTrash /></button>
        </div>
      </div>
      <div className="h-0.5 bg-neutral-200 rounded-full mb-3" />

      {/* Tasks */}
      <div className="flex flex-col gap-2 flex-1 min-h-[4rem]">
        {tasks.length === 0 ? (
          <div className={`flex flex-col items-center justify-center py-8 text-center border border-dashed rounded-xl transition ${dragOver ? "border-neutral-400 bg-neutral-50" : "border-neutral-200"}`}>
            <p className="text-xs text-neutral-400">{dragOver ? "Drop here" : "No tasks yet"}</p>
            {!dragOver && (
              <button onClick={() => onAddTask(column.id)} className="mt-2 text-xs text-neutral-500 hover:text-neutral-900 underline underline-offset-2 transition">Add one</button>
            )}
          </div>
        ) : (
          tasks.map(task => (
            <TaskCard
              key={task.id}
              task={task}
              onView={onViewTask}
              onEdit={onEditTask}
              onDelete={onDeleteTask}
              onDragStart={() => {}}
              onDragEnd={() => {}}
              draggedTask={draggedTask}
            />
          ))
        )}
      </div>

      {/* Add task at bottom */}
      <button
        onClick={() => onAddTask(column.id)}
        className="mt-3 flex items-center justify-center gap-1.5 w-full py-2 rounded-lg border border-dashed border-neutral-200 text-xs text-neutral-400 hover:border-neutral-400 hover:text-neutral-600 hover:bg-white transition"
      >
        <IconPlus size={12}/> Add task
      </button>
    </div>
  );
}

// ── BoardDetail page ─────────────────────────────────────────────────────────
export default function BoardDetail() {
  const { boardId } = useParams();
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("user") || "null");

  const [board, setBoard]     = useState(null);
  const [columns, setColumns] = useState([]);
  const [tasks, setTasks]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");

  // Drag state
  const [draggedTask, setDraggedTask] = useState(null);

  // Detail panel
  const [detailTask, setDetailTask] = useState(null);

  // Column modal
  const [colModalOpen, setColModalOpen]   = useState(false);
  const [editingColumn, setEditingColumn] = useState(null);

  // Task modal
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask]     = useState(null);
  const [defaultColId, setDefaultColId]   = useState(null);

  // Delete dialogs
  const [deleteColTarget, setDeleteColTarget]   = useState(null);
  const [deleteTaskTarget, setDeleteTaskTarget] = useState(null);
  const [deleteLoading, setDeleteLoading]       = useState(false);

  // Toast
  const [toast, setToast] = useState(null);
  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // AI-drafted tasks (from chat) live directly in `tasks` flagged
  // `__draft: true` — there's no separate popup/dialog state anymore.
  // Confirmation happens inline in the chat panel itself.
  const [savingDrafts, setSavingDrafts] = useState(false);

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchAll = useCallback(async () => {
    setLoading(true);
    setFetchError("");
    try {
      const [boardRes, colsRes, tasksRes] = await Promise.all([
        api.get(`/boards/${boardId}`),
        api.get("/columns/"),
        api.get("/tasks/"),
      ]);
      setBoard(boardRes.data);
      const boardCols = colsRes.data.filter(c => c.board_id === Number(boardId));
      setColumns(boardCols);
      const colIds = new Set(boardCols.map(c => c.id));
      setTasks(tasksRes.data.filter(t => colIds.has(t.column_id)));
    } catch (err) {
      setFetchError(err?.response?.data?.detail || "Failed to load. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [boardId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ── Column CRUD ────────────────────────────────────────────────────────────
  const handleCreateColumn = async (name) => {
    const { data } = await api.post("/columns/", { name, board_id: Number(boardId) });
    setColumns(prev => [...prev, data]);
    showToast("Column added.");
  };
  const handleEditColumn = async (name) => {
    const { data } = await api.put(`/columns/${editingColumn.id}`, { name, board_id: editingColumn.board_id });
    setColumns(prev => prev.map(c => c.id === data.id ? data : c));
    showToast("Column renamed.");
  };
  const handleDeleteColumn = async () => {
    if (!deleteColTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/columns/${deleteColTarget.id}`);
      setColumns(prev => prev.filter(c => c.id !== deleteColTarget.id));
      setTasks(prev => prev.filter(t => t.column_id !== deleteColTarget.id));
      showToast("Column deleted.");
      setDeleteColTarget(null);
    } catch (err) {
      showToast(err?.response?.data?.detail || "Delete failed.", "error");
    } finally {
      setDeleteLoading(false);
    }
  };

  // ── Task CRUD ──────────────────────────────────────────────────────────────
  const handleCreateTask = async (form) => {
    const { data } = await api.post("/tasks/", form);
    setTasks(prev => [...prev, data]);
    showToast("Task created.");
  };
  const handleEditTask = async (form) => {
    const { data } = await api.put(`/tasks/${editingTask.id}`, form);
    setTasks(prev => prev.map(t => t.id === data.id ? data : t));
    // Update detail panel if open
    setDetailTask(prev => prev?.id === data.id ? data : prev);
    showToast("Task updated.");
  };
  const handleDeleteTask = async () => {
    if (!deleteTaskTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/tasks/${deleteTaskTarget.id}`);
      setTasks(prev => prev.filter(t => t.id !== deleteTaskTarget.id));
      if (detailTask?.id === deleteTaskTarget.id) setDetailTask(null);
      showToast("Task deleted.");
      setDeleteTaskTarget(null);
    } catch (err) {
      showToast(err?.response?.data?.detail || "Delete failed.", "error");
    } finally {
      setDeleteLoading(false);
    }
  };

  // ── Drag & drop move task between columns ──────────────────────────────────
  const handleDropTask = async (taskId, newColumnId) => {
    const task = tasks.find(t => t.id === taskId);
    if (!task || task.column_id === newColumnId) return;
    // Optimistic update
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, column_id: newColumnId } : t));
    try {
      await api.put(`/tasks/${taskId}`, { column_id: newColumnId });
      showToast("Task moved.");
    } catch {
      // Revert on failure
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, column_id: task.column_id } : t));
      showToast("Move failed.", "error");
    }
  };

  // ── AI chat → board bridge ───────────────────────────────────────────────
  // Every AI response that drafts/edits/clears tasks sends back the
  // COMPLETE resulting set (never a diff), so we always fully replace
  // whatever draft cards currently exist with the new set. This is what
  // makes "remove the CI task" or "make that one high priority" work: the
  // AI sees the current pending list (sent with every chat message, see
  // ChatWidget) and returns the corrected full list, which lands here.
  const handleTasksDrafted = (newColumns = [], newTasks = []) => {
    setColumns(prev => {
      const existingIds = new Set(prev.map(c => c.id));
      const toAdd = newColumns
        .filter(c => !existingIds.has(c.id))
        .map(c => ({ id: c.id, name: c.name, board_id: Number(boardId) }));
      return toAdd.length ? [...prev, ...toAdd] : prev;
    });

    setTasks(prev => {
      const withoutOldDrafts = prev.filter(t => !t.__draft);
      const freshDrafts = newTasks.map((t, i) => ({
        id: `draft-${Date.now()}-${i}`,
        __draft: true,
        title: t.title,
        description: t.description || "",
        priority: t.priority || "medium",
        column_id: t.column_id,
      }));
      return [...withoutOldDrafts, ...freshDrafts];
    });
  };

  // The AI created a real column (already persisted server-side once the
  // user confirmed it in chat) — just reflect it into local board state.
  const handleColumnCreated = (col) => {
    setColumns(prev => (prev.some(c => c.id === col.id) ? prev : [...prev, { id: col.id, name: col.name, board_id: Number(boardId) }]));
    showToast(`Column "${col.name}" added.`);
  };

  // Called from the chat panel's inline "Yes" button — saves every
  // currently-drafted task for real, one by one, and swaps each in place.
  const handleSaveAllDrafts = async () => {
    const drafts = tasks.filter(t => t.__draft);
    if (!drafts.length) return { success: true, savedCount: 0, failedCount: 0 };

    setSavingDrafts(true);
    let savedCount = 0;
    let failedCount = 0;

    for (const draft of drafts) {
      try {
        const { data } = await api.post("/tasks/", {
          title: draft.title,
          description: draft.description,
          priority: draft.priority,
          column_id: draft.column_id,
        });
        setTasks(prev => prev.map(t => (t.id === draft.id ? data : t)));
        savedCount += 1;
      } catch {
        failedCount += 1;
      }
    }

    setSavingDrafts(false);
    if (failedCount) {
      showToast(`${failedCount} task(s) failed to save — you can ask the assistant to try again.`, "error");
    }
    return { success: failedCount === 0, savedCount, failedCount };
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-neutral-50 flex flex-col">
      {/* Header */}
      <header className="border-b border-neutral-200 bg-white sticky top-0 z-10 shrink-0">
        <div className="px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex items-center gap-2 font-semibold tracking-tight shrink-0">
              <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center font-bold text-sm">S</div>
              StackPilot
            </div>
            <span className="text-neutral-300">/</span>
            <button onClick={() => navigate("/boards")} className="flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-900 transition shrink-0">
              <IconBack /> Boards
            </button>
            {board && (
              <>
                <span className="text-neutral-300">/</span>
                <span className="text-sm font-medium text-neutral-900 truncate">{board.name}</span>
              </>
            )}
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => { setEditingColumn(null); setColModalOpen(true); }}
              className="flex items-center gap-2 bg-neutral-950 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-neutral-800 transition"
            >
              <IconPlus size={14}/> Add column
            </button>
            <div className="w-8 h-8 rounded-full bg-neutral-900 text-white flex items-center justify-center font-semibold text-xs">
              {user?.name?.charAt(0) || "U"}
            </div>
            <button onClick={logout} className="text-sm px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">Sign out</button>
          </div>
        </div>
      </header>

      {/* Board description */}
      {board?.description && (
        <div className="border-b border-neutral-100 bg-white px-6 py-2.5">
          <p className="text-xs text-neutral-500">{board.description}</p>
        </div>
      )}

      {/* Kanban canvas */}
      <div className="flex-1 overflow-x-auto">
        <div className="flex gap-4 p-6" style={{ minWidth: "max-content", minHeight: "calc(100vh - 64px)" }}>

          {/* Loading */}
          {loading && [1,2,3].map(i => (
            <div key={i} className="w-72 shrink-0">
              <div className="h-6 bg-neutral-200 rounded-lg animate-pulse mb-3 w-28"/>
              <div className="h-0.5 bg-neutral-200 rounded mb-3"/>
              <div className="space-y-2">
                {[1,2].map(j => <div key={j} className="h-24 bg-white border border-neutral-200 rounded-xl animate-pulse"/>)}
              </div>
            </div>
          ))}

          {/* Error */}
          {!loading && fetchError && (
            <div className="flex items-center justify-center w-full py-24">
              <div className="text-center">
                <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">{fetchError}</p>
                <button onClick={fetchAll} className="mt-4 text-sm text-neutral-600 hover:text-neutral-900 underline underline-offset-2">Try again</button>
              </div>
            </div>
          )}

          {/* Empty board */}
          {!loading && !fetchError && columns.length === 0 && (
            <div className="flex flex-col items-center justify-center w-full py-24 text-center">
              <div className="w-12 h-12 rounded-2xl bg-neutral-100 flex items-center justify-center mb-4"><IconPlus size={20}/></div>
              <p className="text-base font-medium text-neutral-900">No columns yet</p>
              <p className="mt-1.5 text-sm text-neutral-500">Add a column to start organising tasks.</p>
              <button onClick={() => { setEditingColumn(null); setColModalOpen(true); }} className="mt-6 flex items-center gap-2 bg-neutral-950 text-white text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-neutral-800 transition">
                <IconPlus size={14}/> Add first column
              </button>
            </div>
          )}

          {/* Columns */}
          {!loading && !fetchError && columns.map(col => (
            <ColumnPanel
              key={col.id}
              column={col}
              tasks={tasks.filter(t => t.column_id === col.id)}
              draggedTask={draggedTask}
              onAddTask={(colId) => { setEditingTask(null); setDefaultColId(colId); setTaskModalOpen(true); }}
              onEditColumn={(col) => { setEditingColumn(col); setColModalOpen(true); }}
              onDeleteColumn={setDeleteColTarget}
              onViewTask={setDetailTask}
              onEditTask={(task) => { setEditingTask(task); setTaskModalOpen(true); }}
              onDeleteTask={setDeleteTaskTarget}
              onDropTask={handleDropTask}
            />
          ))}

          {/* Trailing add-column lane */}
          {!loading && !fetchError && columns.length > 0 && (
            <div className="w-72 shrink-0">
              <button
                onClick={() => { setEditingColumn(null); setColModalOpen(true); }}
                className="w-full h-32 flex flex-col items-center justify-center gap-2 border border-dashed border-neutral-300 rounded-xl text-neutral-400 hover:border-neutral-400 hover:text-neutral-600 hover:bg-white transition"
              >
                <IconPlus size={18}/><span className="text-sm font-medium">Add column</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Task detail panel ── */}
      {detailTask && (
        <TaskDetail
          task={detailTask}
          columns={columns}
          onClose={() => setDetailTask(null)}
          onEdit={(task) => { setEditingTask(task); setTaskModalOpen(true); }}
          onDelete={setDeleteTaskTarget}
        />
      )}

      {/* ── Modals ── */}
      <ColumnModal
        open={colModalOpen}
        onClose={() => { setColModalOpen(false); setEditingColumn(null); }}
        onSubmit={editingColumn ? handleEditColumn : handleCreateColumn}
        initial={editingColumn}
      />
      <TaskModal
        open={taskModalOpen}
        onClose={() => { setTaskModalOpen(false); setEditingTask(null); }}
        onSubmit={editingTask ? handleEditTask : handleCreateTask}
        initial={editingTask}
        columns={columns}
        defaultColumnId={defaultColId}
      />
      <ConfirmDialog
        open={!!deleteColTarget}
        onClose={() => setDeleteColTarget(null)}
        onConfirm={handleDeleteColumn}
        loading={deleteLoading}
        title={`Delete column "${deleteColTarget?.name}"?`}
        message="All tasks inside this column will also be removed. This cannot be undone."
      />
      <ConfirmDialog
        open={!!deleteTaskTarget}
        onClose={() => setDeleteTaskTarget(null)}
        onConfirm={handleDeleteTask}
        loading={deleteLoading}
        title={`Delete "${deleteTaskTarget?.title}"?`}
        message="This task will be permanently deleted."
      />

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-5 right-5 z-50 text-sm font-medium px-4 py-2.5 rounded-lg shadow-lg border ${toast.type === "error" ? "bg-red-50 border-red-100 text-red-700" : "bg-white border-neutral-200 text-neutral-900"}`}>
          {toast.msg}
        </div>
      )}

      {/* Analyze-your-project launcher — mirrors the chat launcher, bottom-left. */}
      <button
        onClick={() => navigate(`/boards/${boardId}/analyze`)}
        title="Project insights"
        className="fixed bottom-5 left-5 z-40 w-12 h-12 rounded-full shadow-lg flex items-center justify-center bg-neutral-950 text-white hover:bg-neutral-800 transition"
      >
        <IconAnalyze />
      </button>

      {/* RAG-connected chat assistant, scoped to this board. Confirmation
          for AI-drafted tasks happens inline in the chat panel — no popup. */}
      <ChatWidget
        boardId={boardId}
        pendingTasks={tasks
          .filter(t => t.__draft)
          .map(t => ({
            title: t.title,
            description: t.description,
            priority: t.priority,
            column_id: t.column_id,
            column_name: columns.find(c => c.id === t.column_id)?.name || "",
          }))}
        onTasksDrafted={handleTasksDrafted}
        onColumnCreated={handleColumnCreated}
        onSaveAllDrafts={handleSaveAllDrafts}
      />
    </div>
  );
}