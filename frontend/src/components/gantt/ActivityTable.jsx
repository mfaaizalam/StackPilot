import { useState } from "react";
import { FLAGS, TONE, errText, fmtDate, num, pkr } from "../../utils/ganttFormat.js";

const inputCls = "w-full text-sm text-ink border border-line rounded-lg px-2.5 py-1.5 bg-surface focus:outline-none focus:ring-2 focus:ring-brand/20";
const iso = (d) => new Date(d).toISOString().slice(0, 10);

function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-medium text-ink mb-1">{label}</span>
      {children}
      {hint && <span className="block text-[10px] text-ink-muted/70 mt-0.5">{hint}</span>}
    </label>
  );
}

// One form for both "add" and "edit"; money and hours stay strings until the server parses them.
function ActivityForm({ initial, others, onSave, onCancel, busy, error }) {
  const today = iso(Date.now());
  const [f, setF] = useState({
    name: initial?.name ?? "", phase: initial?.phase ?? "",
    start_date: initial?.start_date ?? today, end_date: initial?.end_date ?? today,
    planned_hours: initial?.planned_hours ?? "0", actual_hours: initial?.actual_hours ?? "0",
    estimated_cost: initial?.estimated_cost ?? "0", actual_cost: initial?.actual_cost ?? "0",
    progress_pct: initial?.progress_pct ?? 0, depends_on: initial?.depends_on ?? [],
  });
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  const toggleDep = (id) => setF((p) => ({ ...p, depends_on: p.depends_on.includes(id) ? p.depends_on.filter((d) => d !== id) : [...p.depends_on, id] }));
  const badDates = f.end_date < f.start_date;

  const submit = (e) => {
    e.preventDefault();
    onSave({ ...f, name: f.name.trim(), phase: f.phase.trim() || null, progress_pct: Number(f.progress_pct) });
  };

  return (
    <form onSubmit={submit} className="bg-surface-2/60 border border-line rounded-card p-4 space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="sm:col-span-2"><Field label="Activity name"><input required maxLength={200} className={inputCls} value={f.name} onChange={set("name")} /></Field></div>
        <Field label="Phase" hint="Used to group costs and funding"><input maxLength={100} className={inputCls} value={f.phase} onChange={set("phase")} /></Field>
        <Field label={`Progress: ${f.progress_pct}%`}><input type="range" min="0" max="100" className="w-full" value={f.progress_pct} onChange={set("progress_pct")} /></Field>
        <Field label="Start date"><input required type="date" className={inputCls} value={f.start_date} onChange={set("start_date")} /></Field>
        <Field label="End date"><input required type="date" min={f.start_date} className={inputCls} value={f.end_date} onChange={set("end_date")} /></Field>
        <Field label="Planned hours"><input type="number" min="0" step="0.5" className={inputCls} value={f.planned_hours} onChange={set("planned_hours")} /></Field>
        <Field label="Actual hours"><input type="number" min="0" step="0.5" className={inputCls} value={f.actual_hours} onChange={set("actual_hours")} /></Field>
        <Field label="Estimated cost (PKR)"><input type="number" min="0" step="0.01" className={inputCls} value={f.estimated_cost} onChange={set("estimated_cost")} /></Field>
        <Field label="Actual cost (PKR)"><input type="number" min="0" step="0.01" className={inputCls} value={f.actual_cost} onChange={set("actual_cost")} /></Field>
      </div>
      {others.length > 0 && (
        <fieldset>
          <legend className="text-[11px] font-medium text-ink mb-1">Depends on</legend>
          <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
            {others.map((o) => (
              <label key={o.id} className={`text-xs border rounded-full px-2.5 py-1 cursor-pointer transition ${f.depends_on.includes(o.id) ? "bg-brand text-brand-fg border-brand" : "bg-surface text-ink-muted border-line hover:bg-surface-2"}`}>
                <input type="checkbox" className="sr-only" checked={f.depends_on.includes(o.id)} onChange={() => toggleDep(o.id)} />
                {o.name.length > 28 ? `${o.name.slice(0, 28)}…` : o.name}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {(badDates || error) && <p className="text-xs text-danger">{badDates ? "End date cannot be before the start date." : error}</p>}
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="text-sm px-3 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 transition">Cancel</button>
        <button type="submit" disabled={busy || badDates || !f.name.trim()} className="text-sm font-medium px-4 py-1.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">
          {busy ? "Saving…" : "Save activity"}
        </button>
      </div>
    </form>
  );
}

export default function ActivityTable({ activities, canEdit, actions }) {
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [err, setErr] = useState("");

  const save = (mutation, args, done) =>
    mutation.mutate(args, { onSuccess: () => { setErr(""); done(); }, onError: (e) => setErr(errText(e)) });

  const remove = (a) => {
    if (window.confirm(`Delete “${a.name}”? Finance increments tied to it stay, but become project-wide.`))
      actions.deleteActivity.mutate(a.id, { onError: (e) => setErr(errText(e)) });
  };

  return (
    <div className="space-y-3">
      {canEdit && (
        <div className="flex justify-end">
          <button onClick={() => { setAdding((v) => !v); setEditingId(null); setErr(""); }} className="text-sm font-medium px-3.5 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition">
            {adding ? "Close form" : "Add activity"}
          </button>
        </div>
      )}
      {adding && <ActivityForm others={activities} busy={actions.addActivity.isPending} error={err}
        onCancel={() => setAdding(false)} onSave={(body) => save(actions.addActivity, body, () => setAdding(false))} />}

      <div className="bg-surface border border-line rounded-card overflow-x-auto">
        <table className="w-full text-xs min-w-[860px]">
          <thead>
            <tr className="text-left text-ink-muted/70 border-b border-line bg-surface-2/50">
              <th className="px-3 py-2 font-medium">Activity</th><th className="px-3 font-medium">Dates</th>
              <th className="px-3 font-medium">Hours (actual / planned)</th><th className="px-3 font-medium text-right">Estimated</th>
              <th className="px-3 font-medium text-right">Actual</th><th className="px-3 font-medium text-right">Variance</th>
              <th className="px-3 font-medium">Progress</th><th className="px-3 font-medium">Status</th>{canEdit && <th className="px-3" />}
            </tr>
          </thead>
          <tbody>
            {activities.length === 0 && <tr><td colSpan={9} className="px-3 py-8 text-center text-ink-muted">No activities yet.</td></tr>}
            {activities.map((a) => {
              const over = num(a.cost_variance) > 0;
              return [
                <tr key={a.id} className="border-b border-line/60 align-top">
                  <td className="px-3 py-2.5"><p className="font-medium text-ink">{a.name}</p><p className="text-ink-muted">{a.phase || "No phase"}</p></td>
                  <td className="px-3 py-2.5 whitespace-nowrap">{fmtDate(a.start_date)}<br /><span className="text-ink-muted">to {fmtDate(a.end_date)} · {a.duration_days}d</span></td>
                  <td className="px-3 py-2.5 whitespace-nowrap">{num(a.actual_hours)} / {num(a.planned_hours)}
                    {num(a.hours_variance) !== 0 && <span className={`block ${num(a.hours_variance) > 0 ? "text-danger" : "text-ink-muted"}`}>{num(a.hours_variance) > 0 ? "+" : ""}{num(a.hours_variance)} h</span>}</td>
                  <td className="px-3 py-2.5 text-right whitespace-nowrap">{pkr(a.estimated_cost)}</td>
                  <td className="px-3 py-2.5 text-right whitespace-nowrap">{pkr(a.actual_cost)}</td>
                  <td className={`px-3 py-2.5 text-right whitespace-nowrap ${over ? "text-danger font-medium" : "text-ink-muted"}`}>
                    {num(a.cost_variance) > 0 ? "+" : ""}{pkr(a.cost_variance)}{a.cost_variance_pct !== null && <span className="block">{a.cost_variance_pct}%</span>}</td>
                  <td className="px-3 py-2.5 w-28">
                    <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden"><div className="h-full bg-brand" style={{ width: `${a.progress_pct}%` }} /></div>
                    <p className="mt-1 text-ink-muted">{a.progress_pct}% done · {a.elapsed_pct}% time</p>
                  </td>
                  <td className="px-3 py-2.5"><div className="flex flex-wrap gap-1">
                    {a.flags.length === 0 ? <span className={`px-2 py-0.5 rounded-full ${TONE.success}`}>On track</span>
                      : a.flags.map((f) => <span key={f} className={`px-2 py-0.5 rounded-full whitespace-nowrap ${TONE[FLAGS[f]?.tone || "muted"]}`}>{FLAGS[f]?.label || f}</span>)}
                  </div></td>
                  {canEdit && <td className="px-3 py-2.5 whitespace-nowrap text-right">
                    <button onClick={() => { setEditingId(editingId === a.id ? null : a.id); setAdding(false); setErr(""); }} className="text-ink-muted hover:text-ink mr-3">Edit</button>
                    <button onClick={() => remove(a)} className="text-danger/80 hover:text-danger">Delete</button>
                  </td>}
                </tr>,
                editingId === a.id && (
                  <tr key={`${a.id}-form`}><td colSpan={9} className="px-3 py-3">
                    <ActivityForm initial={a} others={activities.filter((o) => o.id !== a.id)} busy={actions.updateActivity.isPending} error={err}
                      onCancel={() => setEditingId(null)} onSave={(patch) => save(actions.updateActivity, { id: a.id, patch }, () => setEditingId(null))} />
                  </td></tr>
                ),
              ];
            })}
          </tbody>
        </table>
      </div>
      {err && !adding && editingId === null && <p className="text-xs text-danger">{err}</p>}
    </div>
  );
}
