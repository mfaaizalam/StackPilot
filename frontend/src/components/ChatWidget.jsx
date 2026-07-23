import { useState, useRef, useEffect } from "react";
import api from "../api/axios.js";
import ReactMarkdown from "react-markdown";

// ── Icons (same hand-drawn style as the rest of the app) ─────────────────────
function IconChat({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M2 3.5h12v7H6.5L3.5 13v-2.5H2v-7z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" fill="none" />
    </svg>
  );
}
function IconClose() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>;
}
function IconSend() {
  return <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M2 8l12-5.5L9.5 14l-1.7-5.3L2 8z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round" /></svg>;
}
function IconSparkle({ size = 14 }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="none"><path d="M8 1.5l1.1 3.4L12.5 6l-3.4 1.1L8 10.5 6.9 7.1 3.5 6l3.4-1.1L8 1.5z" fill="currentColor" /></svg>;
}
function IconCheck() {
  return <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

// ── Typing indicator ─────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-3.5 py-2.5">
      {[0, 1, 2].map(i => (
        <span key={i} className="w-1.5 h-1.5 rounded-full bg-neutral-400 animate-bounce" style={{ animationDelay: `${i * 0.12}s` }} />
      ))}
    </div>
  );
}

// ── Single chat bubble ───────────────────────────────────────────────────────
function ChatBubble({ role, message, error }) {
  if (role === "system") {
    return (
      <div className="flex justify-center">
        <div className="flex items-center gap-1.5 bg-neutral-900 text-white text-[11px] font-medium px-3 py-1.5 rounded-full text-center">
          <IconCheck /> {message}
        </div>
      </div>
    );
  }

  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
<div
  className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
    isUser
      ? "bg-neutral-950 text-white"
      : error
      ? "bg-red-50 text-red-700 border border-red-100"
      : "bg-neutral-100 text-neutral-800"
  }`}
>
  <ReactMarkdown
    components={{
      h1: ({ children }) => (
        <h1 className="text-xl font-bold mb-4">{children}</h1>
      ),
      h2: ({ children }) => (
        <h2 className="text-lg font-bold mt-4 mb-2">{children}</h2>
      ),
      p: ({ children }) => (
        <p className="mb-2 whitespace-pre-wrap">{children}</p>
      ),
      strong: ({ children }) => (
        <strong className="font-bold">{children}</strong>
      ),
    }}
  >
    {message}
  </ReactMarkdown>
</div>
    </div>
  );
}

// ── Chat panel + floating launcher ───────────────────────────────────────────
// Talks to the backend RAG endpoint: POST /boards/{boardId}/chat
// Body: { message, pending_tasks }  →  Response: { role, message, action }
//
// pending_tasks is always the CURRENT set of unsaved draft cards on the
// board (passed in via the `pendingTasks` prop) — sent on every request so
// the AI can add to, edit, or remove from that exact batch when the user
// asks for a change, instead of only ever creating something new.
//
// `action` (when present) is one of:
//   { type: "draft_tasks", columns: [{id,name}], tasks: [{title,description,priority,column_id,column_name}] }
//     → the COMPLETE new set of pending tasks (may be shorter, longer, or
//       edited compared to before — always a full replace, never a diff).
//   { type: "create_column", column: {id,name} }
//     → already persisted server-side; just needs reflecting into state.
//
// There is no popup here. Confirmation happens in a bar pinned above the
// composer (rendered whenever pendingTasks.length > 0), not a modal.
export default function ChatWidget({ boardId, pendingTasks = [], onTasksDrafted, onColumnCreated, onSaveAllDrafts }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [loadError, setLoadError] = useState("");
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending || !boardId) return;

    const hadPendingBefore = pendingTasks.length > 0;

    setLoadError("");
    setMessages(prev => [...prev, { role: "user", message: text }]);
    setInput("");
    setSending(true);

    try {
      const { data } = await api.post(`/boards/${boardId}/chat`, {
        message: text,
        pending_tasks: pendingTasks.map(t => ({
          title: t.title,
          description: t.description || "",
          priority: t.priority || "medium",
          column_id: t.column_id,
          column_name: t.column_name,
        })),
      });

      const newMessages = [{ role: "assistant", message: data.message }];

      if (data.action?.type === "draft_tasks") {
        const cols = data.action.columns || [];
        const newTasks = data.action.tasks || [];
        onTasksDrafted?.(cols, newTasks);

        if (newTasks.length === 0) {
          newMessages.push({ role: "system", message: "Cleared the pending tasks." });
        } else if (!hadPendingBefore) {
          newMessages.push({
            role: "system",
            message: `Drafted ${newTasks.length} task${newTasks.length === 1 ? "" : "s"}${cols.length ? ` and ${cols.length} column${cols.length === 1 ? "" : "s"}` : ""}.`,
          });
        } else {
          newMessages.push({ role: "system", message: `Updated the pending tasks — ${newTasks.length} ready.` });
        }
      } else if (data.action?.type === "create_column" && data.action.column) {
        onColumnCreated?.(data.action.column);
        newMessages.push({ role: "system", message: `Added column "${data.action.column.name}" to the board.` });
      }

      setMessages(prev => [...prev, ...newMessages]);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Something went wrong reaching the assistant.";
      setMessages(prev => [...prev, { role: "assistant", message: detail, error: true }]);
      setLoadError(detail);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const handleConfirmSave = async () => {
    if (!onSaveAllDrafts || confirming) return;
    setConfirming(true);
    const result = await onSaveAllDrafts();
    setConfirming(false);
    if (result?.savedCount) {
      setMessages(prev => [
        ...prev,
        { role: "system", message: `Saved ${result.savedCount} task${result.savedCount === 1 ? "" : "s"} to the board.` },
      ]);
    }
  };

  const handleWantChanges = () => {
    setMessages(prev => [...prev, { role: "assistant", message: "Sure — tell me what you'd like to change." }]);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  return (
    <>
      {/* Floating launcher */}
      <button
        onClick={() => setOpen(v => !v)}
        title="Ask the project assistant"
        className={`fixed bottom-5 right-5 z-40 w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition ${
          open ? "bg-white border border-neutral-200 text-neutral-700" : "bg-neutral-950 text-white hover:bg-neutral-800"
        }`}
      >
        {open ? <IconClose /> : <IconChat />}
        {!open && pendingTasks.length > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
            {pendingTasks.length}
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-20 right-5 z-40 w-[23rem] max-w-[calc(100vw-2.5rem)] h-[32rem] max-h-[calc(100vh-8rem)] bg-white border border-neutral-200 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-100 shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center">
                <IconSparkle />
              </div>
              <div>
                <p className="text-sm font-semibold text-neutral-900 leading-none">Stack Pilot Assistant</p>
                <p className="text-[11px] text-neutral-400 mt-0.5">Stack Pilot Assistant can make mistakes.</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition"
            >
              <IconClose />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-neutral-50">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center px-4">
                <div className="w-10 h-10 rounded-xl bg-neutral-100 flex items-center justify-center mb-3 text-neutral-400">
                  <IconSparkle size={16} />
                </div>
                <p className="text-sm font-medium text-neutral-700">Ask about this board</p>
                <p className="mt-1 text-xs text-neutral-400 leading-relaxed">
                  Try "create the whole board" or "add a task for CI setup".
                </p>
              </div>
            )}

            {messages.map((m, i) => (
              <ChatBubble key={i} role={m.role} message={m.message} error={m.error} />
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="bg-neutral-100 rounded-xl">
                  <TypingDots />
                </div>
              </div>
            )}
          </div>

          {/* Inline confirm bar — replaces any popup. Lives right above the
              composer, inside the chat panel, and only shows while there
              are actually unsaved drafts on the board. */}
          {pendingTasks.length > 0 && (
            <div className="px-4 py-3 border-t border-neutral-100 bg-amber-50/60 shrink-0">
              <p className="text-sm text-neutral-800 font-medium">
                Would you like to save {pendingTasks.length === 1 ? "this task" : `these ${pendingTasks.length} tasks`}?
              </p>
              <div className="mt-2 flex gap-2">
                <button
                  onClick={handleConfirmSave}
                  disabled={confirming}
                  className="px-3 py-1.5 rounded-lg bg-neutral-950 text-white text-xs font-medium hover:bg-neutral-800 disabled:opacity-50 transition"
                >
                  {confirming ? "Saving…" : "Yes"}
                </button>
                <button
                  onClick={handleWantChanges}
                  disabled={confirming}
                  className="px-3 py-1.5 rounded-lg border border-neutral-300 text-neutral-700 text-xs font-medium hover:bg-white disabled:opacity-50 transition"
                >
                  Want to add some changes
                </button>
              </div>
            </div>
          )}

          {/* Composer */}
          <div className="border-t border-neutral-100 p-3 shrink-0 bg-white">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about tasks, priorities, progress…"
                className="flex-1 resize-none max-h-24 text-sm px-3 py-2.5 rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-400 transition placeholder:text-neutral-400"
              />
              <button
                onClick={send}
                disabled={sending || !input.trim()}
                title="Send"
                className="w-9 h-9 shrink-0 flex items-center justify-center rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 disabled:opacity-40 disabled:hover:bg-neutral-950 transition"
              >
                <IconSend />
              </button>
            </div>
            {loadError && <p className="mt-1.5 text-[11px] text-red-500">{loadError}</p>}
          </div>
        </div>
      )}
    </>
  );
}