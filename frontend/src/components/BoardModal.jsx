import { useState, useEffect } from "react";

export default function BoardModal({ open, onClose, onSubmit, initial }) {
  const [form, setForm] = useState({ name: "", description: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setForm(initial ? { name: initial.name, description: initial.description || "" } : { name: "", description: "" });
      setError("");
    }
  }, [open, initial]);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setError("Board name is required."); return; }
    setLoading(true);
    setError("");
    try {
      await onSubmit(form);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-overlay/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-surface rounded-2xl border border-line shadow-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold tracking-tight text-ink">
            {initial ? "Edit board" : "New board"}
          </h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-ink-muted/70 hover:text-ink hover:bg-surface-2 transition"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">
              Name <span className="text-ink-muted/70">(required)</span>
            </label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Library Management"
              className="w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-muted/70 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/10 transition"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">
              Description <span className="text-ink-muted/70">(optional)</span>
            </label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What is this board for?"
              rows={3}
              className="w-full rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-muted/70 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/10 transition resize-none"
            />
          </div>

          {error && (
            <div className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2">
              {error}
            </div>
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
              className="flex-1 py-2.5 rounded-lg bg-brand text-brand-fg text-sm font-medium hover:bg-brand-hover disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? (initial ? "Saving…" : "Creating…") : (initial ? "Save changes" : "Create board")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}