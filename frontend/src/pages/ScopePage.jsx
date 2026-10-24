import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../api/axios.js";
import { KEYS } from "../api/queries.js";

const inputClass =
  "w-full rounded-lg border border-line bg-surface text-ink px-3.5 py-2.5 text-sm placeholder:text-ink-muted/60 outline-none focus:border-ink-muted transition";

export default function ScopePage() {
  const { boardId } = useParams();
  const queryClient = useQueryClient();

  const { data: board, isLoading, error } = useQuery({
    queryKey: ["board", boardId],
    queryFn: () => api.get(`/boards/${boardId}`).then((r) => r.data),
    enabled: Boolean(boardId),
  });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null); // { text, type }
  const timer = useRef(null);

  // Load server values into the form whenever the board (or project) changes.
  useEffect(() => {
    if (board) {
      setName(board.name || "");
      setDescription(board.description || "");
    }
  }, [board?.id, board?.name, board?.description]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => clearTimeout(timer.current), []);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), 3000);
  };

  const dirty =
    board && (name.trim() !== (board.name || "") || description.trim() !== (board.description || ""));

  const save = async (e) => {
    e.preventDefault();
    if (!name.trim()) return flash("Project name is required.", "error");
    setSaving(true);
    try {
      const { data } = await api.put(`/boards/${boardId}`, {
        name: name.trim(),
        description: description.trim(),
      });
      queryClient.setQueryData(["board", boardId], (prev) => ({ ...(prev || {}), ...data }));
      queryClient.setQueryData(KEYS.boards, (prev = []) =>
        prev.map((b) => (b.id === data.id ? { ...b, ...data } : b))
      );
      flash("Scope saved.");
    } catch (err) {
      flash(err?.response?.data?.detail || "Could not save.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="border-b border-line bg-surface sticky top-0 z-10">
        <div className="px-3 sm:px-6 py-3">
          <h1 className="text-lg font-semibold tracking-tight">Project Scope</h1>
          <p className="text-xs text-ink-muted mt-0.5">What you are building. The SRS is generated from this description.</p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {isLoading ? (
          <div className="h-72 bg-surface border border-line rounded-2xl animate-pulse" />
        ) : error ? (
          <div className="bg-surface border border-dashed border-line rounded-2xl px-6 py-14 text-center">
            <p className="text-sm text-danger">
              {error?.response?.data?.detail || "Could not load this project."}
            </p>
            <Link to="/boards" className="mt-4 inline-block text-sm text-ink-muted hover:text-ink underline underline-offset-2">
              Back to projects
            </Link>
          </div>
        ) : (
          <form onSubmit={save} className="bg-surface border border-line rounded-2xl p-5 sm:p-6 space-y-5">
            <div>
              <label htmlFor="scope-name" className="block text-sm font-medium mb-1.5">Project name</label>
              <input
                id="scope-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={120}
                placeholder="e.g. Hospital Management System"
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="scope-desc" className="block text-sm font-medium mb-1.5">Project description</label>
              <textarea
                id="scope-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={10}
                placeholder="Who is it for, what should it do, and what is out of scope? A paragraph or two is enough."
                className={`${inputClass} resize-y leading-relaxed`}
              />
              <p className="mt-1.5 text-xs text-ink-muted/80">{description.trim().length} characters</p>
            </div>

            <div className="flex items-center justify-between gap-3 flex-wrap">
              <Link to={`/boards/${boardId}/srs`} className="text-sm text-ink-muted hover:text-ink underline underline-offset-2">
                Continue to Requirements →
              </Link>
              <button
                type="submit"
                disabled={saving || !dirty}
                className="bg-brand text-brand-fg text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-40 transition"
              >
                {saving ? "Saving…" : "Save scope"}
              </button>
            </div>
          </form>
        )}
      </div>

      {msg && (
        <div className={`fixed bottom-5 right-5 z-50 text-sm font-medium px-4 py-2.5 rounded-lg shadow-lg border ${msg.type === "error" ? "bg-danger-soft border-danger/20 text-danger" : "bg-surface border-line text-ink"}`}>
          {msg.text}
        </div>
      )}
    </div>
  );
}