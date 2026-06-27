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
        className="absolute inset-0 bg-neutral-950/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-white rounded-2xl border border-neutral-200 shadow-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold tracking-tight text-neutral-900">
            {initial ? "Edit board" : "New board"}
          </h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1.5">
              Name <span className="text-neutral-400">(required)</span>
            </label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Library Management"
              className="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm placeholder:text-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1.5">
              Description <span className="text-neutral-400">(optional)</span>
            </label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What is this board for?"
              rows={3}
              className="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm placeholder:text-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10 transition resize-none"
            />
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="flex gap-2 pt-1">
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
              className="flex-1 py-2.5 rounded-lg bg-neutral-950 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? (initial ? "Saving…" : "Creating…") : (initial ? "Save changes" : "Create board")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}