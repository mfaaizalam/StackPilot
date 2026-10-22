import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useDeploymentActions, useDocs } from "../../api/deployment.js";
import { errText, fmtDate } from "../../utils/ganttFormat.js";
import { md } from "./mdComponents.jsx";

const CATS = [["plan", "Deployment plan"], ["configuration", "Configuration"], ["supporting", "Supporting"]];
const inputCls = "w-full text-sm text-ink border border-line rounded-lg px-2.5 py-2 bg-surface focus:outline-none focus:ring-2 focus:ring-brand/20";

function DocForm({ initial, busy, error, onSave, onCancel }) {
  const [f, setF] = useState({ title: initial?.title ?? "", category: initial?.category ?? "supporting", content: initial?.content ?? "", url: initial?.url ?? "" });
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSave({ ...f, title: f.title.trim(), url: f.url.trim() || null }); }} className="bg-surface-2/60 border border-line rounded-card p-4 space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label className="block sm:col-span-2"><span className="block text-[11px] font-medium mb-1">Title</span><input required maxLength={200} className={inputCls} value={f.title} onChange={set("title")} /></label>
        <label className="block"><span className="block text-[11px] font-medium mb-1">Type</span>
          <select className={inputCls} value={f.category} onChange={set("category")}>{CATS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      </div>
      <label className="block"><span className="block text-[11px] font-medium mb-1">Content (Markdown supported)</span>
        <textarea rows={7} maxLength={20000} className={`${inputCls} font-mono text-xs`} value={f.content} onChange={set("content")} placeholder="Server details, config steps, checklists... Do not paste passwords or secret keys." /></label>
      <label className="block"><span className="block text-[11px] font-medium mb-1">Link (optional)</span><input type="url" maxLength={500} className={inputCls} value={f.url} onChange={set("url")} placeholder="https://" /></label>
      {error && <p className="text-xs text-danger">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="text-sm px-3 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 transition">Cancel</button>
        <button type="submit" disabled={busy || !f.title.trim()} className="text-sm font-medium px-4 py-1.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">{busy ? "Saving…" : "Save document"}</button>
      </div>
    </form>
  );
}

export default function SupportingDocs({ boardId, canEdit }) {
  const { data: docs, isLoading, error } = useDocs(boardId);
  const { addDoc, updateDoc, deleteDoc } = useDeploymentActions(boardId);
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [open, setOpen] = useState(null);
  const [err, setErr] = useState("");
  const run = (m, args, done) => m.mutate(args, { onSuccess: () => { setErr(""); done(); }, onError: (e) => setErr(errText(e)) });
  const label = Object.fromEntries(CATS);

  if (isLoading) return <div className="h-32 bg-surface border border-line rounded-card animate-pulse" />;
  if (error) return <p className="text-sm text-danger">{errText(error, "Could not load the documents.")}</p>;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-ink-muted">Deployment plans, configuration details and supporting notes for this project.</p>
        {canEdit && <button onClick={() => { setAdding((v) => !v); setEditingId(null); setErr(""); }} className="text-sm font-medium px-3.5 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition shrink-0">{adding ? "Close form" : "Add document"}</button>}
      </div>
      {adding && <DocForm busy={addDoc.isPending} error={err} onCancel={() => setAdding(false)} onSave={(b) => run(addDoc, b, () => setAdding(false))} />}
      {docs.length === 0 && !adding && <p className="text-sm text-ink-muted bg-surface border border-dashed border-ink-muted/40 rounded-card px-4 py-10 text-center">No documents yet.</p>}
      {docs.map((d) => (
        <div key={d.id} className="bg-surface border border-line rounded-card">
          <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
            <button onClick={() => setOpen(open === d.id ? null : d.id)} className="text-left min-w-0" aria-expanded={open === d.id}>
              <p className="text-sm font-medium text-ink truncate">{d.title}</p>
              <p className="text-[11px] text-ink-muted">{label[d.category]} · updated {d.updated_at ? fmtDate(d.updated_at.slice(0, 10)) : ""}</p>
            </button>
            <div className="flex items-center gap-3 text-xs">
              {d.url && <a href={d.url} target="_blank" rel="noopener noreferrer" className="text-brand underline">Open link</a>}
              {canEdit && <>
                <button onClick={() => { setEditingId(editingId === d.id ? null : d.id); setAdding(false); setErr(""); }} className="text-ink-muted hover:text-ink">Edit</button>
                <button onClick={() => window.confirm(`Delete “${d.title}”?`) && deleteDoc.mutate(d.id, { onError: (e) => setErr(errText(e)) })} className="text-danger/80 hover:text-danger">Delete</button></>}
            </div>
          </div>
          {editingId === d.id && <div className="px-4 pb-4"><DocForm initial={d} busy={updateDoc.isPending} error={err} onCancel={() => setEditingId(null)} onSave={(patch) => run(updateDoc, { id: d.id, patch }, () => setEditingId(null))} /></div>}
          {open === d.id && editingId !== d.id && <div className="px-4 pb-4 border-t border-line pt-3">
            {d.content ? <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{d.content}</ReactMarkdown> : <p className="text-xs text-ink-muted">No content. Use Edit to add some.</p>}</div>}
        </div>
      ))}
      {err && !adding && editingId === null && <p className="text-xs text-danger">{err}</p>}
    </div>
  );
}
