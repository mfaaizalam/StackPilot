import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../api/axios.js";
import ColumnModal from "../components/ColumnModal.jsx";
import TaskModal from "../components/TaskModal.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import ChatWidget from "../components/ChatWidget.jsx";

import { DragDropProvider, useDraggable, useDroppable } from "@dnd-kit/react";
import { PointerSensor, PointerActivationConstraints } from "@dnd-kit/dom";

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
function IconDots() {
  return <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="3" r="1" fill="currentColor"/><circle cx="7" cy="7" r="1" fill="currentColor"/><circle cx="7" cy="11" r="1" fill="currentColor"/></svg>;
}
function IconClose() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>;
}
function IconSearch() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5"/><path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>;
}

// ── Look & feel ──────────────────────────────────────────────────────────────
// Sticky-note colour follows priority, so the board can be read at a glance.
const NOTE = {
  high:   { bg: "#FFC4B8", fold: "#EFA091", pin: "#D9442E", label: "High" },
  medium: { bg: "#FFE78A", fold: "#EACB55", pin: "#C98A00", label: "Medium" },
  low:    { bg: "#C3E9CD", fold: "#98D1A6", pin: "#2A9559", label: "Low" },
};
const noteFor = (priority) => NOTE[(priority || "low").toLowerCase()] || NOTE.low;

// Column accent follows the column's meaning; unknown names cycle a palette.
const FALLBACK_ACCENTS = ["#E4568C", "#17A2B8", "#8E7CC3", "#E67E22", "#4C9AFF"];
function columnAccent(name, index) {
  const n = (name || "").toLowerCase();
  if (/backlog/.test(n)) return "#8A94A6";
  if (/ready|to ?do/.test(n)) return "#3B8EEA";
  if (/progress|doing/.test(n)) return "#F0A020";
  if (/test|review|qa/.test(n)) return "#9B6BFF";
  if (/done|complete/.test(n)) return "#2FB86B";
  return FALLBACK_ACCENTS[index % FALLBACK_ACCENTS.length];
}

// Stable tilt per note (-2.1° … +2.1°) so notes look hand-placed but never jump.
function tiltFor(id) {
  const s = String(id);
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 997;
  return ((h % 7) - 3) * 0.7;
}

const CONFETTI_COLORS = ["#FFE78A", "#FFC4B8", "#C3E9CD", "#9CC9FF", "#C9B6FF"];

const BOARD_STYLES = `
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;600&display=swap');
.sp-hand { font-family: 'Caveat', 'Segoe Print', 'Bradley Hand', cursive; }
.sp-note {
  transform: rotate(var(--rot));
  transition: transform .18s ease, box-shadow .18s ease;
  box-shadow: 0 1px 1px rgba(0,0,0,.12), 0 6px 10px -4px rgba(0,0,0,.22);
}
.sp-note:hover { transform: rotate(0deg) translateY(-3px) scale(1.025); box-shadow: 0 2px 2px rgba(0,0,0,.12), 0 14px 18px -6px rgba(0,0,0,.3); }
.sp-lifted { transform: rotate(3deg) scale(1.05); box-shadow: 0 18px 28px -8px rgba(0,0,0,.4); }
@keyframes sp-fall { 0% { transform: translateY(-10vh) rotate(0deg); opacity: 1; } 100% { transform: translateY(105vh) rotate(540deg); opacity: .9; } }
.sp-confetti { position: fixed; top: 0; width: 10px; height: 14px; border-radius: 2px; animation: sp-fall 1.5s ease-in forwards; pointer-events: none; z-index: 60; }
@media (prefers-reduced-motion: reduce) { .sp-note { transition: none; } .sp-note:hover { transform: rotate(var(--rot)); } }
`;

// ── Traceability: where this task came from in the SRS ──────────────────────
const isDoneCol = (name) => /^done$/i.test((name || "").trim());

function TraceSection({ boardId, task }) {
  // Cached per task: re-opening the same task does not hit the API again.
  // Any write request (see axios interceptor) marks ["trace"] stale, so
  // dependency statuses refresh after a task is moved or edited.
  const {
    data: trace,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["trace", boardId, task?.id],
    queryFn: () =>
      api.get(`/boards/${boardId}/tasks/${task.id}/trace`).then((r) => r.data),
    enabled: !!task?.requirement_id,
  });

  if (!task?.requirement_id) return null;
  const box = "bg-surface-2 rounded-card p-3 border border-line";
  const label = "text-[11px] text-ink-muted/70 font-medium uppercase tracking-wide mb-1.5";

  if (isLoading) return <div className="h-24 bg-surface-2 border border-line rounded-card animate-pulse" />;
  if (isError || !trace) return <p className="text-xs text-ink-muted/70">Could not load the requirement details.</p>;
  if (!trace.linked) return <p className="text-xs text-ink-muted/70">{trace.reason}</p>;

  const r = trace.requirement;
  const waiting = (trace.depends_on || []).filter(d => d.column && !isDoneCol(d.column));
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-ink-muted/70 font-medium uppercase tracking-wide">Traceability</p>
        <span className="text-[11px] font-medium text-ink-muted bg-surface-2 border border-line rounded-full px-2 py-0.5">
          {trace.requirement_id} · SRS v{trace.srs_version}
        </span>
      </div>

      {!trace.srs_is_latest && (
        <p className="text-xs text-warning bg-warning-soft border border-warning/20 rounded-lg px-3 py-2">
          Generated from SRS v{trace.srs_version}; a newer version exists. Use "Add missing" in SRS Studio to pick up new requirements.
        </p>
      )}
      {trace.note && <p className="text-xs text-warning bg-warning-soft border border-warning/20 rounded-lg px-3 py-2">{trace.note}</p>}

      {r && (
        <div className={box}>
          <p className={label}>Requirement{r.actor ? ` · ${r.actor}` : r.category ? ` · ${r.category}` : ""}</p>
          <p className="text-sm text-ink leading-relaxed">{r.statement}</p>
          {r.metric && <p className="text-xs text-ink-muted mt-1.5"><span className="font-medium">Target:</span> {r.metric}</p>}
          {r.acceptance_criteria?.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-ink-muted list-disc pl-4">
              {r.acceptance_criteria.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          )}
        </div>
      )}

      {trace.use_cases?.length > 0 && (
        <div className={box}>
          <p className={label}>Use case{trace.use_cases.length > 1 ? "s" : ""}</p>
          <div className="space-y-2">
            {trace.use_cases.map(u => (
              <details key={u.id} className="group">
                <summary className="cursor-pointer text-sm text-ink font-medium list-none flex items-center justify-between">
                  <span>{u.id} · {u.name}</span>
                  <span className="text-[11px] text-ink-muted/70 font-normal">{u.actor}</span>
                </summary>
                <ol className="mt-1.5 list-decimal pl-5 space-y-0.5 text-xs text-ink-muted">
                  {u.main_flow.map((step, i) => <li key={i}>{step}</li>)}
                </ol>
              </details>
            ))}
          </div>
        </div>
      )}

      {(trace.depends_on?.length > 0 || trace.blocks?.length > 0) && (
        <div className={box}>
          {trace.depends_on?.length > 0 && (
            <>
              <p className={label}>Suggested to start after</p>
              {waiting.length > 0 && (
                <p className="text-xs text-warning bg-warning-soft border border-warning/20 rounded-lg px-2.5 py-1.5 mb-2">
                  Waiting on {waiting.length} unfinished task{waiting.length > 1 ? "s" : ""}.
                </p>
              )}
              <ul className="space-y-1.5">
                {trace.depends_on.map(d => (
                  <li key={d.requirement_id} className="flex items-center justify-between gap-2 text-xs text-ink">
                    <span className="truncate">{d.requirement_id} {d.title}</span>
                    <span className={`shrink-0 px-2 py-0.5 rounded-full border text-[11px] ${d.column ? (isDoneCol(d.column) ? "bg-success-soft text-success border-success/20" : "bg-surface text-ink-muted border-line") : "bg-surface text-ink-muted/70 border-line"}`}>
                      {d.column || "no task"}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {trace.blocks?.length > 0 && (
            <div className={trace.depends_on?.length > 0 ? "mt-3 pt-3 border-t border-line" : ""}>
              <p className={label}>Unblocks</p>
              <ul className="space-y-1.5">
                {trace.blocks.map(d => (
                  <li key={d.requirement_id} className="flex items-center justify-between gap-2 text-xs text-ink">
                    <span className="truncate">{d.requirement_id} {d.title}</span>
                    <span className="shrink-0 px-2 py-0.5 rounded-full border text-[11px] bg-surface text-ink-muted border-line">{d.column || "no task"}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Task Detail slide-over panel ─────────────────────────────────────────────
function TaskDetail({ boardId, task, columns, onClose, onEdit, onDelete }) {
  if (!task) return null;
  const col = columns.find(c => c.id === task.column_id);
  const note = noteFor(task.priority);
  return (
    <>
      <div className="fixed inset-0 z-30 bg-ink/20 backdrop-blur-[2px]" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 z-40 w-full max-w-sm bg-surface border-l border-line shadow-2xl flex flex-col">
        {/* Colour strip matches the sticky note */}
        <div className="h-2 shrink-0" style={{ background: note.bg }} />
        <div className="flex items-center justify-between px-5 py-3 border-b border-line">
          <span className="text-xs text-ink-muted/70 font-medium">Task #{task.id}</span>
          <div className="flex items-center gap-1">
            <button onClick={() => { onClose(); onEdit(task); }} className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink px-2.5 py-1.5 rounded-md hover:bg-surface-2 transition font-medium">
              <IconEdit /> Edit
            </button>
            <button onClick={() => { onClose(); onDelete(task); }} className="flex items-center gap-1.5 text-xs text-danger hover:text-danger/80 px-2.5 py-1.5 rounded-md hover:bg-danger-soft transition font-medium">
              <IconTrash /> Delete
            </button>
            <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-ink hover:bg-surface-2 transition ml-1">
              <IconClose />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          <h2 className="sp-hand text-3xl font-semibold text-ink leading-tight">{task.title}</h2>

          {task.description ? (
            <p className="text-sm text-ink-muted leading-relaxed whitespace-pre-wrap">{task.description}</p>
          ) : (
            <p className="text-sm text-ink-muted/70 italic">No description provided.</p>
          )}

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="bg-surface-2 rounded-card p-3 border border-line">
              <p className="text-[11px] text-ink-muted/70 font-medium mb-1.5">Priority</p>
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-ink">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: note.pin }} />{note.label}
              </span>
            </div>
            <div className="bg-surface-2 rounded-card p-3 border border-line">
              <p className="text-[11px] text-ink-muted/70 font-medium mb-1.5">Column</p>
              <p className="text-sm font-medium text-ink">{col?.name || "—"}</p>
            </div>
            {task.estimate_points ? (
              <div className="bg-surface-2 rounded-card p-3 border border-line col-span-2">
                <p className="text-[11px] text-ink-muted/70 font-medium mb-1.5">Estimate</p>
                <p className="text-sm font-medium text-ink">{task.estimate_points} story point{task.estimate_points === 1 ? "" : "s"} <span className="text-xs text-ink-muted/70 font-normal">· relative size, edit freely</span></p>
              </div>
            ) : null}
          </div>

          <TraceSection boardId={boardId} task={task} />
        </div>
      </div>
    </>
  );
}

// ── Sticky note (draggable task card) ────────────────────────────────────────
function TaskCard({ task, onView, onEdit, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isDraft = !!task.__draft;
  const { ref, isDragging } = useDraggable({ id: `task-${task.id}`, disabled: isDraft });

  const note = noteFor(task.priority);
  // The tilt lives on an inner wrapper so it never fights dnd-kit's own transform.
  const noteStyle = isDraft
    ? { "--rot": "0deg", background: "transparent", border: "2px dashed rgba(128,128,128,.5)", boxShadow: "none" }
    : { "--rot": `${tiltFor(task.id)}deg`, background: note.bg };

  return (
    <div
      ref={ref}
      onClick={() => { if (!isDraft && !menuOpen && !isDragging) onView(task); }}
      className="relative cursor-pointer select-none pt-2"
      style={{ touchAction: isDraft ? "auto" : "none" }}
    >
      <div
        className={`sp-note group relative rounded-[3px] px-4 pt-5 pb-3 ${isDragging ? "sp-lifted" : ""}`}
        style={{ ...noteStyle, color: isDraft ? undefined : "#2B2A26" }}
      >
        {/* Pin */}
        {!isDraft && (
          <span
            className="absolute -top-2 left-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full"
            style={{ background: `radial-gradient(circle at 35% 30%, #fff8 0 15%, ${note.pin} 40%)`, boxShadow: "0 2px 3px rgba(0,0,0,.35)" }}
          />
        )}

        {/* Action menu */}
        {!isDraft && (
          <div className="absolute top-1.5 right-1.5" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setMenuOpen(v => !v)}
              className="w-6 h-6 flex items-center justify-center rounded-md opacity-0 group-hover:opacity-100 hover:bg-black/10 transition"
              aria-label="Note actions"
            >
              <IconDots />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 top-7 z-20 w-32 bg-surface border border-line rounded-lg shadow-lg py-1 text-sm">
                  <button onClick={() => { setMenuOpen(false); onEdit(task); }} className="w-full flex items-center gap-2 px-3 py-2 text-ink hover:bg-surface-2 transition">
                    <IconEdit /> Edit
                  </button>
                  <button onClick={() => { setMenuOpen(false); onDelete(task); }} className="w-full flex items-center gap-2 px-3 py-2 text-danger hover:bg-danger-soft transition">
                    <IconTrash /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {task.requirement_id && !isDraft && (
          <span className="inline-block mb-1 text-[11px] font-medium rounded px-1.5 py-0.5" style={{ background: "rgba(255,255,255,.55)" }}>
            {task.requirement_id}
          </span>
        )}

        <p className={`sp-hand text-[22px] font-semibold leading-[1.1] pr-4 ${isDraft ? "text-ink-muted" : ""}`}>{task.title}</p>

        {task.description && (
          <p className={`mt-1.5 text-xs line-clamp-2 leading-relaxed ${isDraft ? "text-ink-muted" : "opacity-75"}`}>{task.description}</p>
        )}

        <div className="mt-3 flex items-center gap-2">
          {isDraft ? (
            <span className="text-[11px] font-medium text-ink-muted">Draft · not saved yet</span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium">
              <span className="w-2 h-2 rounded-full" style={{ background: note.pin }} />{note.label}
            </span>
          )}
          {!isDraft && task.estimate_points ? (
            <span
              title="Estimated story points (relative size)"
              className="ml-auto w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-semibold"
              style={{ background: "rgba(255,255,255,.6)" }}
            >
              {task.estimate_points}
            </span>
          ) : null}
        </div>

        {/* Folded corner */}
        {!isDraft && (
          <span
            className="absolute bottom-0 right-0 w-5 h-5 rounded-tl-[3px]"
            style={{ background: `linear-gradient(135deg, transparent 50%, ${note.fold} 50%)` }}
          />
        )}
      </div>
    </div>
  );
}

// ── Column lane (with drop zone and quick add) ──────────────────────────────
function ColumnPanel({
  column, accent, tasks, totalCount, filtering,
  onAddTask, onQuickAdd, onEditColumn, onDeleteColumn, onViewTask, onEditTask, onDeleteTask,
}) {
  const { ref, isDropTarget } = useDroppable({ id: `column-${column.id}` });
  const [adding, setAdding] = useState(false);
  const [text, setText] = useState("");

  const submit = async () => {
    const title = text.trim();
    if (!title) { setAdding(false); return; }
    setText("");
    await onQuickAdd(column.id, title); // keep the box open so several notes can be added in a row
  };

  return (
    <div
      ref={ref}
      className="flex flex-col w-72 shrink-0 rounded-2xl p-3 transition-all duration-150"
      style={{
        background: `${accent}${isDropTarget ? "26" : "12"}`,
        border: `1px solid ${accent}${isDropTarget ? "99" : "33"}`,
        borderTop: `5px solid ${accent}`,
        boxShadow: isDropTarget ? `0 0 0 3px ${accent}33` : "none",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-semibold text-ink truncate">{column.name}</span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: `${accent}2E`, color: accent }}>
            {filtering ? `${tasks.length}/${totalCount}` : tasks.length}
          </span>
        </div>
        <div className="flex items-center gap-0.5">
          <button onClick={() => onEditColumn(column)} title="Rename" className="w-6 h-6 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-ink hover:bg-surface/70 transition"><IconEdit /></button>
          <button onClick={() => onDeleteColumn(column)} title="Delete" className="w-6 h-6 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-danger hover:bg-danger-soft transition"><IconTrash /></button>
        </div>
      </div>

      {/* Notes */}
      <div className="flex flex-col gap-3 flex-1 min-h-[5rem]">
        {tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center rounded-xl border-2 border-dashed" style={{ borderColor: `${accent}55` }}>
            <p className="text-xs text-ink-muted">
              {isDropTarget ? "Drop it here" : filtering && totalCount > 0 ? "No matching notes" : "Nothing here yet"}
            </p>
          </div>
        ) : (
          tasks.map(task => (
            <TaskCard key={task.id} task={task} onView={onViewTask} onEdit={onEditTask} onDelete={onDeleteTask} />
          ))
        )}
      </div>

      {/* Quick add */}
      {adding ? (
        <div className="mt-3">
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
              if (e.key === "Escape") { setText(""); setAdding(false); }
            }}
            onBlur={() => { if (!text.trim()) setAdding(false); }}
            placeholder="Write a note, press Enter"
            className="w-full px-3 py-2 rounded-lg text-sm bg-surface text-ink border outline-none"
            style={{ borderColor: accent }}
          />
          <p className="mt-1 text-[11px] text-ink-muted/80">Enter to add · Esc to close · <button onMouseDown={(e) => { e.preventDefault(); onAddTask(column.id); }} className="underline underline-offset-2">full form</button></p>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="mt-3 flex items-center justify-center gap-1.5 w-full py-2 rounded-lg text-xs font-medium transition hover:bg-surface/70"
          style={{ color: accent, border: `1px dashed ${accent}77` }}
        >
          <IconPlus size={12} /> Add note
        </button>
      )}
    </div>
  );
}

// ── BoardDetail page ─────────────────────────────────────────────────────────
// Rendered inside the app layout (sidebar). The global header (logo, nav,
// user, sign out) lives in the sidebar; this page only has a slim toolbar.
export default function BoardDetail() {
  const { boardId } = useParams();
  const queryClient = useQueryClient();

  const cacheKey = ["board-data", boardId];
  const cached = queryClient.getQueryData(cacheKey);

  const [board, setBoard]     = useState(cached?.board ?? null);
  const [columns, setColumns] = useState(cached?.columns ?? []);
  const [tasks, setTasks]     = useState(cached?.tasks ?? []);
  const [loading, setLoading] = useState(!cached);
  const [fetchError, setFetchError] = useState("");

  const [detailTask, setDetailTask] = useState(null);

  const [colModalOpen, setColModalOpen]   = useState(false);
  const [editingColumn, setEditingColumn] = useState(null);

  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask]     = useState(null);
  const [defaultColId, setDefaultColId]   = useState(null);

  const [deleteColTarget, setDeleteColTarget]   = useState(null);
  const [deleteTaskTarget, setDeleteTaskTarget] = useState(null);
  const [deleteLoading, setDeleteLoading]       = useState(false);

  // Filters
  const [query, setQuery] = useState("");
  const [prioFilter, setPrioFilter] = useState("all");
  const filtering = query.trim() !== "" || prioFilter !== "all";

  // Confetti when a note lands in Done
  const [burst, setBurst] = useState(0);
  const confetti = useMemo(
    () => Array.from({ length: 28 }, (_, i) => ({
      left: `${(i * 37 + burst * 13) % 100}%`,
      delay: `${((i * 53) % 40) / 100}s`,
      color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
    })),
    [burst]
  );
  const burstTimer = useRef(null);
  const celebrate = () => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    setBurst(b => b + 1);
    clearTimeout(burstTimer.current);
    burstTimer.current = setTimeout(() => setBurst(0), 1800);
  };
  useEffect(() => () => clearTimeout(burstTimer.current), []);

  // Toast
  const [toast, setToast] = useState(null);
  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const [savingDrafts, setSavingDrafts] = useState(false);

  // ── Fetch ──────────────────────────────────────────────────────────────────
  // Cached for 60 s. Any write request anywhere in the app (see the axios
  // interceptor) marks "board-data" stale, so coming back after creating,
  // moving or generating tasks always refetches. A plain page switch does not.
  // NOTE: this still downloads ALL columns/tasks and filters here. A backend
  // endpoint like GET /boards/{id}/full would remove that over-fetching.
  const fetchAll = useCallback(async (force = false) => {
    const key = ["board-data", boardId];
    const hasCache = !!queryClient.getQueryData(key);
    if (!hasCache || force) setLoading(true);
    setFetchError("");
    try {
      const result = await queryClient.fetchQuery({
        queryKey: key,
        staleTime: force ? 0 : 60_000,
        queryFn: async () => {
          const [boardRes, colsRes, tasksRes] = await Promise.all([
            api.get(`/boards/${boardId}`),
            api.get("/columns/"),
            api.get("/tasks/"),
          ]);
          const boardCols = colsRes.data.filter(c => c.board_id === Number(boardId));
          const colIds = new Set(boardCols.map(c => c.id));
          return {
            board: boardRes.data,
            columns: boardCols,
            tasks: tasksRes.data.filter(t => colIds.has(t.column_id)),
          };
        },
      });
      setBoard(result.board);
      setColumns(result.columns);
      setTasks(result.tasks);
    } catch (err) {
      setFetchError(err?.response?.data?.detail || "Failed to load. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [boardId, queryClient]);

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
  // One-line quick add straight from a column
  const handleQuickAdd = async (columnId, title) => {
    try {
      const { data } = await api.post("/tasks/", { title, description: "", priority: "medium", column_id: columnId });
      setTasks(prev => [...prev, data]);
    } catch (err) {
      showToast(err?.response?.data?.detail || "Could not add the note.", "error");
    }
  };
  const handleEditTask = async (form) => {
    const { data } = await api.put(`/tasks/${editingTask.id}`, form);
    setTasks(prev => prev.map(t => t.id === data.id ? data : t));
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

  // ── Move task to another column ────────────────────────────────────────────
  const handleDropTask = async (taskId, newColumnId) => {
    const task = tasks.find(t => t.id === taskId);
    if (!task || task.column_id === newColumnId) return;

    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, column_id: newColumnId } : t));

    try {
      await api.put(`/tasks/${taskId}`, { column_id: newColumnId });
      const target = columns.find(c => c.id === newColumnId);
      if (isDoneCol(target?.name)) {
        celebrate();
        showToast("Done. Nice work!");
      } else {
        showToast("Task moved.");
      }
    } catch (error) {
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, column_id: task.column_id } : t));
      showToast("Move failed.", "error");
    }
  };

  const handleDragEnd = (event) => {
    if (event.canceled) return;
    const { source, target } = event.operation;
    if (!source || !target) return;
    const taskId = Number(String(source.id).replace("task-", ""));
    const newColumnId = Number(String(target.id).replace("column-", ""));
    if (!taskId || !newColumnId) return;
    handleDropTask(taskId, newColumnId);
  };

  // ── AI chat → board bridge ───────────────────────────────────────────────
  // Every AI response that drafts/edits/clears tasks sends back the
  // COMPLETE resulting set (never a diff), so we always fully replace
  // whatever draft cards currently exist with the new set.
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

  const handleColumnCreated = (col) => {
    setColumns(prev => (prev.some(c => c.id === col.id) ? prev : [...prev, { id: col.id, name: col.name, board_id: Number(boardId) }]));
    showToast(`Column "${col.name}" added.`);
  };

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

  // ── Derived: progress + filtering ──────────────────────────────────────────
  const realTasks = tasks.filter(t => !t.__draft);
  const doneIds = new Set(columns.filter(c => isDoneCol(c.name)).map(c => c.id));
  const doneCount = realTasks.filter(t => doneIds.has(t.column_id)).length;
  const pct = realTasks.length ? Math.round((doneCount / realTasks.length) * 100) : 0;

  const matches = (t) => {
    if (t.__draft) return true;
    if (prioFilter !== "all" && (t.priority || "low").toLowerCase() !== prioFilter) return false;
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return [t.title, t.description, t.requirement_id].some(v => (v || "").toLowerCase().includes(q));
  };

  const PRIO_CHIPS = [
    { key: "all", label: "All", color: "#8A94A6" },
    { key: "high", label: "High", color: NOTE.high.pin },
    { key: "medium", label: "Medium", color: NOTE.medium.pin },
    { key: "low", label: "Low", color: NOTE.low.pin },
  ];

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col">
      <style>{BOARD_STYLES}</style>

      {/* Toolbar */}
      <div className="border-b border-line bg-surface sticky top-0 z-10 shrink-0">
        <div className="px-3 sm:px-6 py-3 flex flex-wrap items-center gap-x-5 gap-y-3">
          <div className="min-w-0">
            <h1 className="text-lg font-semibold tracking-tight text-ink truncate">Kanban Board</h1>
            {realTasks.length > 0 && (
              <div className="mt-1 flex items-center gap-2" title={`${doneCount} of ${realTasks.length} tasks done`}>
                <div className="w-32 h-1.5 rounded-full bg-surface-2 overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: "#2FB86B" }} />
                </div>
                <span className="text-xs text-ink-muted">{doneCount} of {realTasks.length} done</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            {PRIO_CHIPS.map(c => {
              const active = prioFilter === c.key;
              return (
                <button
                  key={c.key}
                  onClick={() => setPrioFilter(c.key)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition"
                  style={active
                    ? { background: `${c.color}22`, borderColor: c.color, color: "inherit" }
                    : { borderColor: "transparent" }}
                  aria-pressed={active}
                >
                  <span className="w-2 h-2 rounded-full" style={{ background: c.color }} />{c.label}
                </button>
              );
            })}
          </div>

          <div className="relative ml-auto flex items-center gap-2">
            <div className="relative">
              <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-muted/70 pointer-events-none"><IconSearch /></span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search notes"
                className="w-40 sm:w-52 pl-8 pr-3 py-1.5 rounded-lg text-sm bg-surface-2 border border-line text-ink outline-none focus:border-ink-muted/60"
              />
            </div>
            <button
              onClick={() => { setEditingColumn(null); setColModalOpen(true); }}
              className="shrink-0 flex items-center gap-1.5 sm:gap-2 bg-brand text-brand-fg text-sm font-medium px-2.5 sm:px-4 py-2 rounded-lg hover:bg-brand-hover transition"
            >
              <IconPlus size={14}/> <span className="hidden sm:inline">Add column</span>
            </button>
          </div>
        </div>
      </div>

      {/* Board */}
      <DragDropProvider
        sensors={(defaults) => [
          ...defaults.filter((sensor) => sensor !== PointerSensor),
          PointerSensor.configure({
            activationConstraints: (event) => {
              if (event.pointerType === "touch") {
                return [new PointerActivationConstraints.Delay({ value: 400, tolerance: 8 })];
              }
              return [new PointerActivationConstraints.Distance({ value: 5 })];
            },
          }),
        ]}
        onDragEnd={handleDragEnd}
      >
        <div className="flex-1 min-w-0 overflow-x-auto">
          <div className="flex gap-5 p-4 sm:p-6 min-h-full items-start" style={{ minWidth: "max-content" }}>

            {loading && [1,2,3].map(i => (
              <div key={i} className="w-72 shrink-0">
                <div className="h-6 bg-line rounded-lg animate-pulse mb-3 w-28"/>
                <div className="space-y-3">
                  {[1,2].map(j => <div key={j} className="h-24 bg-surface border border-line rounded-card animate-pulse"/>)}
                </div>
              </div>
            ))}

            {!loading && fetchError && (
              <div className="flex items-center justify-center w-full py-24">
                <div className="text-center">
                  <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-4 py-3">{fetchError}</p>
                  <button onClick={() => fetchAll(true)} className="mt-4 text-sm text-ink-muted hover:text-ink underline underline-offset-2">Try again</button>
                </div>
              </div>
            )}

            {!loading && !fetchError && columns.length === 0 && (
              <div className="flex flex-col items-center justify-center w-full py-24 text-center">
                <div className="w-12 h-12 rounded-2xl bg-surface-2 flex items-center justify-center mb-4"><IconPlus size={20}/></div>
                <p className="text-base font-medium text-ink">No columns yet</p>
                <p className="mt-1.5 text-sm text-ink-muted">Add a column to start pinning notes.</p>
                <button onClick={() => { setEditingColumn(null); setColModalOpen(true); }} className="mt-6 flex items-center gap-2 bg-brand text-brand-fg text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-brand-hover transition">
                  <IconPlus size={14}/> Add first column
                </button>
              </div>
            )}

            {!loading && !fetchError && columns.map((col, idx) => {
              const colTasks = tasks.filter(t => t.column_id === col.id);
              return (
                <ColumnPanel
                  key={col.id}
                  column={col}
                  accent={columnAccent(col.name, idx)}
                  tasks={colTasks.filter(matches)}
                  totalCount={colTasks.filter(t => !t.__draft).length}
                  filtering={filtering}
                  onAddTask={(colId) => { setEditingTask(null); setDefaultColId(colId); setTaskModalOpen(true); }}
                  onQuickAdd={handleQuickAdd}
                  onEditColumn={(c) => { setEditingColumn(c); setColModalOpen(true); }}
                  onDeleteColumn={setDeleteColTarget}
                  onViewTask={setDetailTask}
                  onEditTask={(task) => { setEditingTask(task); setTaskModalOpen(true); }}
                  onDeleteTask={setDeleteTaskTarget}
                />
              );
            })}

            {!loading && !fetchError && columns.length > 0 && (
              <div className="w-72 shrink-0">
                <button
                  onClick={() => { setEditingColumn(null); setColModalOpen(true); }}
                  className="w-full h-32 flex flex-col items-center justify-center gap-2 border-2 border-dashed border-ink-muted/40 rounded-2xl text-ink-muted/70 hover:border-ink-muted/60 hover:text-ink-muted hover:bg-surface/60 transition"
                >
                  <IconPlus size={18}/><span className="text-sm font-medium">Add column</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </DragDropProvider>

      {/* Confetti */}
      {burst > 0 && confetti.map((c, i) => (
        <span key={`${burst}-${i}`} className="sp-confetti" style={{ left: c.left, background: c.color, animationDelay: c.delay }} />
      ))}

      {detailTask && (
        <TaskDetail
          boardId={boardId}
          task={detailTask}
          columns={columns}
          onClose={() => setDetailTask(null)}
          onEdit={(task) => { setEditingTask(task); setTaskModalOpen(true); }}
          onDelete={setDeleteTaskTarget}
        />
      )}

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

      {toast && (
        <div className={`fixed bottom-5 right-5 z-50 text-sm font-medium px-4 py-2.5 rounded-lg shadow-lg border ${toast.type === "error" ? "bg-danger-soft border-danger/20 text-danger" : "bg-surface border-line text-ink"}`}>
          {toast.msg}
        </div>
      )}

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