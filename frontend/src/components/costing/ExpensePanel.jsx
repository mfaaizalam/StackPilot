import { useState } from "react";
import { errText, fmtDate, num, pkr } from "../../utils/ganttFormat.js";

const CATS = [["labour", "Labour"], ["infrastructure", "Hosting and infrastructure"], ["tools", "Tools and software"], ["licences", "Licences"],
  ["travel", "Travel"], ["training", "Training"], ["contingency", "Contingency"], ["other", "Other"]];
const catLabel = Object.fromEntries(CATS);
const inputCls = "w-full text-sm text-ink border border-line rounded-lg px-2.5 py-1.5 bg-surface focus:outline-none focus:ring-2 focus:ring-brand/20";

function ExpenseForm({ initial, activities, busy, error, onSave, onCancel }) {
  const [f, setF] = useState({
    category: initial?.category ?? "labour", description: initial?.description ?? "",
    estimated_amount: initial?.estimated_amount ?? "0", actual_amount: initial?.actual_amount ?? "0",
    incurred_on: initial?.incurred_on ?? "", activity_id: initial?.activity_id ? String(initial.activity_id) : "",
  });
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  const submit = (e) => {
    e.preventDefault();
    const base = { ...f, description: f.description.trim(), incurred_on: f.incurred_on || null };
    onSave(initial
      ? { ...base, activity_id: f.activity_id ? Number(f.activity_id) : null, clear_activity: !f.activity_id }
      : { ...base, activity_id: f.activity_id ? Number(f.activity_id) : null });
  };
  return (
    <form onSubmit={submit} className="bg-surface-2/60 border border-line rounded-card p-4 space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <label className="block"><span className="block text-[11px] font-medium mb-1">Category</span>
          <select className={inputCls} value={f.category} onChange={set("category")}>{CATS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <div className="sm:col-span-2"><label className="block"><span className="block text-[11px] font-medium mb-1">Description</span>
          <input required maxLength={300} className={inputCls} value={f.description} onChange={set("description")} placeholder="e.g. Developer time, domain, SSL certificate" /></label></div>
        <label className="block"><span className="block text-[11px] font-medium mb-1">Applies to</span>
          <select className={inputCls} value={f.activity_id} onChange={set("activity_id")}>
            <option value="">Whole project</option>{activities.map((a) => <option key={a.id} value={a.id}>{a.name.slice(0, 40)}</option>)}</select></label>
        <label className="block"><span className="block text-[11px] font-medium mb-1">Estimated (PKR)</span>
          <input type="number" min="0" step="0.01" className={inputCls} value={f.estimated_amount} onChange={set("estimated_amount")} /></label>
        <label className="block"><span className="block text-[11px] font-medium mb-1">Actual (PKR)</span>
          <input type="number" min="0" step="0.01" className={inputCls} value={f.actual_amount} onChange={set("actual_amount")} /></label>
        <label className="block"><span className="block text-[11px] font-medium mb-1">Date (optional)</span>
          <input type="date" className={inputCls} value={f.incurred_on} onChange={set("incurred_on")} /></label>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="text-sm px-3 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 transition">Cancel</button>
        <button type="submit" disabled={busy || !f.description.trim()} className="text-sm font-medium px-4 py-1.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">{busy ? "Saving…" : "Save expense"}</button>
      </div>
    </form>
  );
}

export default function ExpensePanel({ data, actions }) {
  const { expenses, activities, can_manage_finance: canManage } = data;
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [err, setErr] = useState("");
  const nameOf = (id) => activities.find((a) => a.id === id)?.name || "Whole project";
  const run = (m, args, done) => m.mutate(args, { onSuccess: () => { setErr(""); done(); }, onError: (e) => setErr(errText(e)) });

  return (
    <div className="space-y-3">
      {canManage && <div className="flex justify-end">
        <button onClick={() => { setAdding((v) => !v); setEditingId(null); setErr(""); }} className="text-sm font-medium px-3.5 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition">{adding ? "Close form" : "Add expense"}</button></div>}
      {adding && <ExpenseForm activities={activities} busy={actions.addExpense.isPending} error={err} onCancel={() => setAdding(false)}
        onSave={(b) => run(actions.addExpense, b, () => setAdding(false))} />}
      <div className="bg-surface border border-line rounded-card overflow-x-auto">
        <table className="w-full text-xs min-w-[760px]">
          <thead><tr className="text-left text-ink-muted/70 border-b border-line bg-surface-2/50">
            <th className="px-3 py-2 font-medium">Description</th><th className="px-3 font-medium">Category</th><th className="px-3 font-medium">Applies to</th>
            <th className="px-3 font-medium text-right">Estimated</th><th className="px-3 font-medium text-right">Actual</th><th className="px-3 font-medium text-right">Variance</th>{canManage && <th />}
          </tr></thead>
          <tbody>
            {expenses.length === 0 && <tr><td colSpan={7} className="px-3 py-8 text-center text-ink-muted">No expense lines yet.</td></tr>}
            {expenses.map((e) => [
              <tr key={e.id} className="border-b border-line/60 align-top">
                <td className="px-3 py-2.5"><p className="font-medium text-ink">{e.description}</p>{e.incurred_on && <p className="text-ink-muted">{fmtDate(e.incurred_on)}</p>}</td>
                <td className="px-3 py-2.5">{catLabel[e.category] || e.category}</td>
                <td className="px-3 py-2.5">{e.activity_id ? nameOf(e.activity_id) : <span className="text-ink-muted">Whole project</span>}</td>
                <td className="px-3 py-2.5 text-right whitespace-nowrap">{pkr(e.estimated_amount)}</td>
                <td className="px-3 py-2.5 text-right whitespace-nowrap">{pkr(e.actual_amount)}</td>
                <td className={`px-3 py-2.5 text-right whitespace-nowrap ${num(e.variance) > 0 ? "text-danger font-medium" : "text-ink-muted"}`}>{num(e.variance) > 0 ? "+" : ""}{pkr(e.variance)}</td>
                {canManage && <td className="px-3 py-2.5 whitespace-nowrap text-right">
                  <button onClick={() => { setEditingId(editingId === e.id ? null : e.id); setAdding(false); setErr(""); }} className="text-ink-muted hover:text-ink mr-3">Edit</button>
                  <button onClick={() => window.confirm("Delete this expense?") && actions.deleteExpense.mutate(e.id, { onError: (x) => setErr(errText(x)) })} className="text-danger/80 hover:text-danger">Delete</button></td>}
              </tr>,
              editingId === e.id && <tr key={`${e.id}-f`}><td colSpan={7} className="px-3 py-3">
                <ExpenseForm initial={e} activities={activities} busy={actions.updateExpense.isPending} error={err} onCancel={() => setEditingId(null)}
                  onSave={(patch) => run(actions.updateExpense, { id: e.id, patch }, () => setEditingId(null))} /></td></tr>,
            ])}
          </tbody>
        </table>
      </div>
      {err && !adding && editingId === null && <p className="text-xs text-danger">{err}</p>}
    </div>
  );
}
