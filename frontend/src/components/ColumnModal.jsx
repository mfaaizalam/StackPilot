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
      <div className="absolute inset-0 bg-neutral-950/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm bg-white rounded-2xl border border-neutral-200 shadow-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold tracking-tight text-neutral-900">
            {initial ? "Rename column" : "Add column"}
          </h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1.5">
              Name
            </label>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. To Do, In Progress, Done"
              className="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm placeholder:text-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-lg border border-neutral-200 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2.5 rounded-lg bg-neutral-950 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition"
            >
              {loading ? (initial ? "Saving…" : "Adding…") : (initial ? "Save" : "Add column")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}