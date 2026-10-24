import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import api from "../api/axios.js";
import { isDemo } from "../demo/demoMode.js";
import useActiveBoardId from "../hooks/useActiveBoardId.js";

// ── Icons ────────────────────────────────────────────────────────────────────
const IconClose = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
);
const IconSend = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M2 8l12-5.5L9.5 14l-1.7-5.3L2 8z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round" /></svg>
);
const IconSparkle = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><path d="M8 1.5l1.1 3.4L12.5 6l-3.4 1.1L8 10.5 6.9 7.1 3.5 6l3.4-1.1L8 1.5z" fill="currentColor" /></svg>
);
const IconCheck = () => (
  <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
);

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-3.5 py-2.5">
      {[0, 1, 2].map((i) => (
        <span key={i} className="w-1.5 h-1.5 rounded-full bg-ink-muted/70 animate-bounce" style={{ animationDelay: `${i * 0.12}s` }} />
      ))}
    </div>
  );
}

function ChatBubble({ role, message, error }) {
  if (role === "system") {
    return (
      <div className="flex justify-center">
        <div className="flex items-center gap-1.5 bg-surface-2 text-ink border border-line text-[11px] font-medium px-3 py-1.5 rounded-full text-center">
          <IconCheck /> {message}
        </div>
      </div>
    );
  }
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[88%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-brand text-brand-fg"
            : error
            ? "bg-danger-soft text-danger border border-danger/20"
            : "bg-surface-2 text-ink"
        }`}
      >
        <ReactMarkdown
          components={{
            h1: ({ children }) => <h1 className="text-xl font-bold mb-4">{children}</h1>,
            h2: ({ children }) => <h2 className="text-lg font-bold mt-4 mb-2">{children}</h2>,
            p: ({ children }) => <p className="mb-2 last:mb-0 whitespace-pre-wrap">{children}</p>,
            strong: ({ children }) => <strong className="font-bold">{children}</strong>,
          }}
        >
          {message}
        </ReactMarkdown>
      </div>
    </div>
  );
}

const notifyBoardChanged = () => window.dispatchEvent(new Event("stackpilot:board-changed"));

// Slide-in assistant. Backend contract (unchanged):
//   POST /boards/{id}/chat  { message, pending_tasks } -> { message, action }
//   action: draft_tasks (COMPLETE new draft set) | create_column (already saved)
//   GET  /boards/{id}/chat  -> history
export default function AssistantPanel({ open, onClose }) {
  const { boardId, board } = useActiveBoardId();
  const demo = isDemo();

  const [messages, setMessages] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadedFor, setLoadedFor] = useState(null);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const boardRef = useRef(boardId);
  boardRef.current = boardId;

  // New project -> fresh conversation (history is per board on the server).
  useEffect(() => {
    setMessages([]);
    setDrafts([]);
    setLoadedFor(null);
    setLoadError("");
  }, [boardId]);

  // Load history the first time the panel opens for a project.
  useEffect(() => {
    if (!open || !boardId || demo || loadedFor === boardId) return;
    let cancelled = false;
    setLoadingHistory(true);
    setLoadError("");
    api
      .get(`/boards/${boardId}/chat`)
      .then(({ data }) => {
        if (cancelled) return;
        setMessages((data || []).map((m) => ({ id: m.id, role: m.role, message: m.message })));
        setLoadedFor(boardId);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err?.response?.data?.detail || "Failed to load chat history.");
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });
    return () => {
      cancelled = true;
      setLoadingHistory(false);
    };
  }, [open, boardId, demo, loadedFor]);

  // Esc closes; focus the composer when opened.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    const t = setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 120);
    return () => {
      document.removeEventListener("keydown", onKey);
      clearTimeout(t);
    };
  }, [open, onClose]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending, drafts.length]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending || !boardId || demo) return;
    const bid = boardId;
    const hadDrafts = drafts.length > 0;

    setLoadError("");
    setMessages((p) => [...p, { role: "user", message: text }]);
    setInput("");
    setSending(true);

    try {
      const { data } = await api.post(`/boards/${bid}/chat`, {
        message: text,
        pending_tasks: drafts.map((d) => ({
          title: d.title,
          description: d.description || "",
          priority: d.priority || "medium",
          column_id: d.column_id,
          column_name: d.column_name,
        })),
      });
      if (bid !== boardRef.current) return; // user switched project mid-request

      const added = [{ role: "assistant", message: data.message }];
      const action = data.action;

      if (action?.type === "draft_tasks") {
        const cols = action.columns || [];
        const tasks = action.tasks || [];
        setDrafts(
          tasks.map((t) => ({
            title: t.title,
            description: t.description || "",
            priority: t.priority || "medium",
            column_id: t.column_id,
            column_name: t.column_name || cols.find((c) => c.id === t.column_id)?.name || "",
          }))
        );
        if (cols.length) notifyBoardChanged(); // new columns are already saved server-side
        added.push({
          role: "system",
          message:
            tasks.length === 0
              ? "Cleared the pending tasks."
              : hadDrafts
              ? `Updated the pending tasks: ${tasks.length} ready.`
              : `Drafted ${tasks.length} task${tasks.length === 1 ? "" : "s"}${cols.length ? ` and ${cols.length} column${cols.length === 1 ? "" : "s"}` : ""}.`,
        });
      } else if (action?.type === "create_column" && action.column) {
        notifyBoardChanged();
        added.push({ role: "system", message: `Added column "${action.column.name}" to the board.` });
      }

      setMessages((p) => [...p, ...added]);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Something went wrong reaching the assistant.";
      setMessages((p) => [...p, { role: "assistant", message: detail, error: true }]);
    } finally {
      setSending(false);
    }
  };

  const saveDrafts = async () => {
    if (!drafts.length || saving) return;
    setSaving(true);
    const failed = [];
    let saved = 0;
    for (const d of drafts) {
      try {
        await api.post("/tasks/", {
          title: d.title,
          description: d.description,
          priority: d.priority,
          column_id: d.column_id,
        });
        saved += 1;
      } catch {
        failed.push(d);
      }
    }
    setDrafts(failed);
    setSaving(false);
    if (saved) notifyBoardChanged();
    setMessages((p) => [
      ...p,
      {
        role: "system",
        message: failed.length
          ? `Saved ${saved}, ${failed.length} failed. Ask me to try again.`
          : `Saved ${saved} task${saved === 1 ? "" : "s"} to the board.`,
      },
    ]);
  };

  const wantChanges = () => {
    setMessages((p) => [...p, { role: "assistant", message: "Sure, tell me what you'd like to change." }]);
    setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 50);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const disabled = !boardId || demo;

  return (
    <aside
      role="dialog"
      aria-label="StackPilot Assistant"
      aria-hidden={!open}
      {...(open ? {} : { inert: "" })}
      className={`fixed right-0 top-12 bottom-0 z-40 w-full sm:w-[26rem] bg-surface text-ink border-l border-line flex flex-col transition-transform duration-300 ease-out motion-reduce:transition-none print:hidden ${
        open ? "translate-x-0 shadow-2xl" : "translate-x-full shadow-none"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-line shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-brand text-brand-fg flex items-center justify-center shrink-0">
            <IconSparkle size={15} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold leading-none">StackPilot Assistant</p>
            <p className="text-[11px] text-ink-muted/70 mt-1 truncate">
              {board?.name ? `${board.name} · ` : ""}AI can make mistakes.
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Close assistant"
          className="w-8 h-8 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-ink hover:bg-surface-2 transition"
        >
          <IconClose />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-canvas">
        {loadingHistory && messages.length === 0 && (
          <div className="h-full flex items-center justify-center"><TypingDots /></div>
        )}

        {!loadingHistory && messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-10 h-10 rounded-xl bg-surface-2 flex items-center justify-center mb-3 text-ink-muted/70">
              <IconSparkle size={16} />
            </div>
            {demo ? (
              <>
                <p className="text-sm font-medium">Assistant unavailable in demo mode</p>
                <p className="mt-1 text-xs text-ink-muted/70 leading-relaxed">The backend is offline, so the assistant can't answer right now.</p>
              </>
            ) : !boardId ? (
              <>
                <p className="text-sm font-medium">Select a project first</p>
                <p className="mt-1 text-xs text-ink-muted/70 leading-relaxed">The assistant answers questions about a specific project.</p>
              </>
            ) : (
              <>
                <p className="text-sm font-medium">Ask about this project</p>
                <p className="mt-1 text-xs text-ink-muted/70 leading-relaxed">
                  Try "create the whole board" or "add a task for CI setup".
                </p>
              </>
            )}
          </div>
        )}

        {messages.map((m, i) => (
          <ChatBubble key={m.id ?? i} role={m.role} message={m.message} error={m.error} />
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-surface-2 rounded-xl"><TypingDots /></div>
          </div>
        )}
      </div>

      {/* Pending drafts: confirm before anything is saved to the board */}
      {drafts.length > 0 && (
        <div className="px-4 py-3 border-t border-line bg-warning-soft/60 shrink-0">
          <p className="text-sm text-ink font-medium">
            Save {drafts.length === 1 ? "this task" : `these ${drafts.length} tasks`} to the board?
          </p>
          <ul className="mt-2 max-h-28 overflow-y-auto space-y-1">
            {drafts.map((d, i) => (
              <li key={i} className="flex items-center justify-between gap-2 text-xs text-ink">
                <span className="truncate">{d.title}</span>
                <span className="shrink-0 text-ink-muted/80">{d.column_name}</span>
              </li>
            ))}
          </ul>
          <div className="mt-2.5 flex gap-2">
            <button
              onClick={saveDrafts}
              disabled={saving}
              className="px-3 py-1.5 rounded-lg bg-brand text-brand-fg text-xs font-medium hover:bg-brand-hover disabled:opacity-50 transition"
            >
              {saving ? "Saving…" : "Yes, save"}
            </button>
            <button
              onClick={wantChanges}
              disabled={saving}
              className="px-3 py-1.5 rounded-lg border border-line text-ink text-xs font-medium hover:bg-surface-2 disabled:opacity-50 transition"
            >
              Want to add some changes
            </button>
          </div>
        </div>
      )}

      {/* Composer */}
      <div className="border-t border-line p-3 shrink-0 bg-surface">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            disabled={disabled}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={disabled ? "Assistant unavailable" : "Ask about tasks, priorities, progress…"}
            className="flex-1 resize-none max-h-24 text-sm text-ink bg-surface px-3 py-2.5 rounded-lg border border-line focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-ink-muted/60 transition placeholder:text-ink-muted/60 disabled:opacity-60"
          />
          <button
            onClick={send}
            disabled={disabled || sending || !input.trim()}
            title="Send"
            className="w-9 h-9 shrink-0 flex items-center justify-center rounded-lg bg-brand text-brand-fg hover:bg-brand-hover disabled:opacity-40 disabled:hover:bg-brand transition"
          >
            <IconSend />
          </button>
        </div>
        {loadError && <p className="mt-1.5 text-[11px] text-danger">{loadError}</p>}
      </div>
    </aside>
  );
}