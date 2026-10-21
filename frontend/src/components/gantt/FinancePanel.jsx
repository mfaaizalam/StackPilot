import { useState } from "react";
import { STATUS_STYLE, errText, fmtDate, pkr } from "../../utils/ganttFormat.js";

const inputCls = "w-full text-sm text-ink border border-line rounded-lg px-2.5 py-1.5 bg-surface focus:outline-none focus:ring-2 focus:ring-brand/20";
const STATUSES = ["planned", "approved", "disbursed"];

// "" = whole project, "p:Design" = a phase, "a:12" = one activity
const targetOf = (i) => (i.activity_id ? `a:${i.activity_id}` : i.phase ? `p:${i.phase}` : "");
const targetPatch = (v) => (v.startsWith("a:") ? { activity_id: Number(v.slice(2)), phase: null } : v.startsWith("p:") ? { phase: v.slice(2), activity_id: null } : { clear_target: true });

function TargetSelect({ value, onChange, activities, phases, className }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={className}>
      <option value="">Whole project</option>
      {phases.length > 0 && <optgroup label="Phase">{phases.map((p) => <option key={p} value={`p:${p}`}>{p}</option>)}</optgroup>}
      {activities.length > 0 && <optgroup label="Activity">{activities.map((a) => <option key={a.id} value={`a:${a.id}`}>{a.name.slice(0, 40)}</option>)}</optgroup>}
    </select>
  );
}

export default function FinancePanel({ data, canManage, actions }) {
  const { summary: s, increments, activities } = data;
  const phases = [...new Set(activities.map((a) => a.phase).filter(Boolean))];
  const [budget, setBudget] = useState(String(Number(s.base_budget)));
  const [form, setForm] = useState({ amount: "", effective_date: new Date().toISOString().slice(0, 10), status: "planned", target: "", note: "" });
  const [err, setErr] = useState("");
  const fail = (e) => setErr(errText(e));
  const nameOf = (id) => activities.find((a) => a.id === id)?.name || "Deleted activity";

  const saveBudget = (e) => { e.preventDefault(); setErr(""); actions.setBudget.mutate(budget || "0", { onError: fail }); };
  const add = (e) => {
    e.preventDefault(); setErr("");
    const { target, ...rest } = form;
    actions.addIncrement.mutate({ ...rest, note: rest.note.trim() || null, ...(target ? targetPatch(target) : {}) },
      { onSuccess: () => setForm((f) => ({ ...f, amount: "", note: "" })), onError: fail });
  };

  return (
    <div className="space-y-5">
      <form onSubmit={saveBudget} className="flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="block text-[11px] font-medium text-ink mb-1">Base budget (PKR), the starting funds before any increment</span>
          <input type="number" min="0" step="0.01" disabled={!canManage} className={`${inputCls} w-56`} value={budget} onChange={(e) => setBudget(e.target.value)} />
        </label>
        {canManage && <button type="submit" disabled={actions.setBudget.isPending} className="text-sm font-medium px-3.5 py-1.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">Save budget</button>}
        <p className="text-xs text-ink-muted">Current base: <b className="text-ink">{pkr(s.base_budget)}</b></p>
      </form>

      {canManage && (
        <form onSubmit={add} className="bg-surface-2/60 border border-line rounded-card p-4">
          <p className="text-xs font-semibold text-ink mb-3">Add finance increment</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <label className="block"><span className="block text-[11px] font-medium mb-1">Amount (PKR)</span>
              <input required type="number" min="0.01" step="0.01" className={inputCls} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
            <label className="block"><span className="block text-[11px] font-medium mb-1">Effective date</span>
              <input required type="date" className={inputCls} value={form.effective_date} onChange={(e) => setForm({ ...form, effective_date: e.target.value })} /></label>
            <label className="block"><span className="block text-[11px] font-medium mb-1">Status</span>
              <select className={inputCls} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>{STATUSES.map((x) => <option key={x} value={x}>{x}</option>)}</select></label>
            <label className="block"><span className="block text-[11px] font-medium mb-1">Applies to</span>
              <TargetSelect className={inputCls} value={form.target} onChange={(v) => setForm({ ...form, target: v })} activities={activities} phases={phases} /></label>
            <label className="block"><span className="block text-[11px] font-medium mb-1">Note</span>
              <input maxLength={300} className={inputCls} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
          </div>
          <div className="mt-3 flex justify-end">
            <button type="submit" disabled={actions.addIncrement.isPending} className="text-sm font-medium px-4 py-1.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">
              {actions.addIncrement.isPending ? "Adding…" : "Add increment"}
            </button>
          </div>
        </form>
      )}
      {err && <p className="text-xs text-danger">{err}</p>}

      <div className="bg-surface border border-line rounded-card overflow-x-auto">
        <table className="w-full text-xs min-w-[640px]">
          <thead><tr className="text-left text-ink-muted/70 border-b border-line bg-surface-2/50">
            <th className="px-3 py-2 font-medium">Effective</th><th className="px-3 font-medium text-right">Amount</th>
            <th className="px-3 font-medium">Status</th><th className="px-3 font-medium">Applies to</th><th className="px-3 font-medium">Note</th>{canManage && <th />}
          </tr></thead>
          <tbody>
            {increments.length === 0 && <tr><td colSpan={6} className="px-3 py-8 text-center text-ink-muted">No finance increments yet.</td></tr>}
            {increments.map((i) => (
              <tr key={i.id} className="border-b border-line/60">
                <td className="px-3 py-2 whitespace-nowrap">{fmtDate(i.effective_date)}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap font-medium">+{pkr(i.amount)}</td>
                <td className="px-3 py-2">
                  {canManage ? (
                    <select aria-label="Increment status" value={i.status}
                      onChange={(e) => actions.updateIncrement.mutate({ id: i.id, patch: { status: e.target.value } }, { onError: fail })}
                      className={`text-xs rounded-full border px-2.5 py-1 capitalize cursor-pointer ${STATUS_STYLE[i.status]}`}>
                      {STATUSES.map((x) => <option key={x} value={x}>{x}</option>)}
                    </select>
                  ) : <span className={`rounded-full border px-2.5 py-1 capitalize ${STATUS_STYLE[i.status]}`}>{i.status}</span>}
                </td>
                <td className="px-3 py-2">
                  {canManage ? (
                    <TargetSelect className="text-xs border border-line rounded-lg px-2 py-1 bg-surface max-w-[180px]" value={targetOf(i)}
                      onChange={(v) => actions.updateIncrement.mutate({ id: i.id, patch: targetPatch(v) }, { onError: fail })}
                      activities={activities} phases={phases} />
                  ) : i.activity_id ? nameOf(i.activity_id) : i.phase || "Whole project"}
                </td>
                <td className="px-3 py-2 text-ink-muted">{i.note || ""}</td>
                {canManage && <td className="px-3 py-2 text-right"><button onClick={() => window.confirm("Delete this increment?") && actions.deleteIncrement.mutate(i.id, { onError: fail })} className="text-danger/80 hover:text-danger">Delete</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-ink-muted/80">
        <b>Planned</b> = expected, not counted yet. <b>Approved</b> = counts toward the committed budget. <b>Disbursed</b> = money received; counts as available funds.
      </p>
    </div>
  );
}
