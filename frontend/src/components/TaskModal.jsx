import { useState, useEffect } from "react";

const PRIORITIES = ["low", "medium", "high"];

export default function TaskModal({ open, onClose, onSubmit, initial, columns, defaultColumnId }) {
  const [form, setForm] = useState({ title: "", description: "", priority: "medium", column_id: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setForm(
        initial
          ? {
              title: initial.title || "",
              description: initial.description || "",
              priority: initial.priority || "medium",
              column_id: initial.column_id ?? "",
            }
          : {
              title: "",
              description: "",
              priority: "medium",
              column_id: defaultColumnId ?? (columns[0]?.id ?? ""),
            }
      );
      setError("");
    }
  }, [open, initial, defaultColumnId, columns]);

  if (!open) return null;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) { setError("Title is required."); return; }
    if (!form.column_id) { setError("Select a column."); return; }
    setLoading(true);
    setError("");
    try {
      await onSubmit({
        ...form,
        title: form.title.trim(),
        column_id: Number(form.column_id),
      });
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-overlay/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-surface text-ink rounded-card border border-line shadow-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold tracking-tight text-ink">
            {initial ? "Edit task" : "New task"}
          </h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-ink hover:bg-surface-2 transition"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">Title</label>
            <input
              autoFocus
              type="text"
              value={form.title}
              onChange={set("title")}
              placeholder="What needs to be done?"
              className="w-full rounded-lg border border-line bg-surface text-ink px-3.5 py-2.5 text-sm placeholder:text-ink-muted/60 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">
              Description <span className="text-ink-muted/70">(optional)</span>
            </label>
            <textarea
              value={form.description}
              onChange={set("description")}
              placeholder="Add more detail…"
              rows={3}
              className="w-full rounded-lg border border-line bg-surface text-ink px-3.5 py-2.5 text-sm placeholder:text-ink-muted/60 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition resize-none"
            />
          </div>

          {/* Priority + Column — side by side */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Priority</label>
              <select
                value={form.priority}
                onChange={set("priority")}
                className="w-full rounded-lg border border-line bg-surface text-ink px-3 py-2.5 text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Column</label>
              <select
                value={form.column_id}
                onChange={set("column_id")}
                className="w-full rounded-lg border border-line bg-surface text-ink px-3 py-2.5 text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
              >
                {columns.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-lg border border-line text-sm font-medium text-ink hover:bg-surface-2 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2.5 rounded-lg bg-brand text-brand-fg text-sm font-medium hover:bg-brand-hover disabled:opacity-50 transition"
            >
              {loading ? (initial ? "Saving…" : "Creating…") : (initial ? "Save task" : "Create task")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}