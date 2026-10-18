import { useState, useEffect } from "react";

export default function ColumnModal({ open, onClose, onSubmit, initial }) {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setName(initial?.name || "");
      setError("");
    }
  }, [open, initial]);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { setError("Column name is required."); return; }
    setLoading(true);
    setError("");
    try {
      await onSubmit(name.trim());
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
      <div className="relative w-full max-w-sm bg-surface text-ink rounded-card border border-line shadow-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold tracking-tight text-ink">
            {initial ? "Rename column" : "Add column"}
          </h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted/70 hover:text-ink hover:bg-surface-2 transition"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">
              Name
            </label>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. To Do, In Progress, Done"
              className="w-full rounded-lg border border-line bg-surface text-ink px-3.5 py-2.5 text-sm placeholder:text-ink-muted/60 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
            />
          </div>

          {error && (
            <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex gap-2">
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
              {loading ? (initial ? "Saving…" : "Adding…") : (initial ? "Save" : "Add column")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}