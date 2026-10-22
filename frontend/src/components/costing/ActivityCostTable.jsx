import { useState } from "react";
import { Link } from "react-router-dom";
import { FLAGS, TONE, errText, num, pkr } from "../../utils/ganttFormat.js";

const COST_FLAGS = ["cost_overrun", "unbudgeted_cost", "burning_faster_than_progress"];
const inputCls = "w-28 text-xs text-ink border border-line rounded-lg px-2 py-1 bg-surface text-right focus:outline-none focus:ring-2 focus:ring-brand/20";

// Activity-wise estimated vs actual cost. Rows with expense lines are read-only here (their lines are the source).
export default function ActivityCostTable({ data, actions, boardId }) {
  const { activities, project_level: pl, can_edit: canEdit } = data;
  const [editing, setEditing] = useState(null); // { id, est, act }
  const [err, setErr] = useState("");

  const save = () => actions.updateActivity.mutate(
    { id: editing.id, patch: { estimated_cost: editing.est || "0", actual_cost: editing.act || "0" } },
    { onSuccess: () => { setEditing(null); setErr(""); }, onError: (e) => setErr(errText(e)) });

  if (!activities.length && !num(pl.estimated) && !num(pl.actual)) {
    return (
      <div className="bg-surface border border-dashed border-ink-muted/40 rounded-card px-4 py-8 text-center">
        <p className="text-sm text-ink-muted">No activities yet. Activity costs appear here once you create activities.</p>
        <Link to={`/boards/${boardId}/timeline`} className="inline-block mt-3 text-sm font-medium px-4 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition">Open Timeline to generate them</Link>
      </div>
    );
  }
  const rows = activities;
  return (
    <div className="space-y-2">
      <div className="bg-surface border border-line rounded-card overflow-x-auto">
        <table className="w-full text-xs min-w-[780px]">
          <thead><tr className="text-left text-ink-muted/70 border-b border-line bg-surface-2/50">
            <th className="px-3 py-2 font-medium">Activity</th><th className="px-3 font-medium text-right">Estimated</th><th className="px-3 font-medium text-right">Actual</th>
            <th className="px-3 font-medium text-right">Variance</th><th className="px-3 font-medium">Budget used</th><th className="px-3 font-medium">Cost from</th><th className="px-3 font-medium">Status</th>{canEdit && <th />}
          </tr></thead>
          <tbody>
            {rows.map((a) => {
              const flags = a.flags.filter((f) => COST_FLAGS.includes(f));
              const manual = a.cost_source === "manual";
              const isEd = editing?.id === a.id;
              return (
                <tr key={a.id} className="border-b border-line/60 align-top">
                  <td className="px-3 py-2.5"><p className="font-medium text-ink">{a.name}</p><p className="text-ink-muted">{a.phase || "No phase"}</p></td>
                  <td className="px-3 py-2.5 text-right whitespace-nowrap">{isEd ? <input type="number" min="0" step="0.01" className={inputCls} value={editing.est} onChange={(e) => setEditing({ ...editing, est: e.target.value })} aria-label="Estimated cost" /> : pkr(a.estimated_cost)}</td>
                  <td className="px-3 py-2.5 text-right whitespace-nowrap">{isEd ? <input type="number" min="0" step="0.01" className={inputCls} value={editing.act} onChange={(e) => setEditing({ ...editing, act: e.target.value })} aria-label="Actual cost" /> : pkr(a.actual_cost)}</td>
                  <td className={`px-3 py-2.5 text-right whitespace-nowrap ${num(a.cost_variance) > 0 ? "text-danger font-medium" : "text-ink-muted"}`}>{num(a.cost_variance) > 0 ? "+" : ""}{pkr(a.cost_variance)}{a.cost_variance_pct !== null && <span className="block">{a.cost_variance_pct}%</span>}</td>
                  <td className="px-3 py-2.5 w-28">
                    {a.budget_used_pct === null ? <span className="text-ink-muted">No estimate</span> : <>
                      <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden"><div className={`h-full ${a.budget_used_pct > 100 ? "bg-danger" : "bg-brand"}`} style={{ width: `${Math.min(a.budget_used_pct, 100)}%` }} /></div>
                      <p className="mt-1 text-ink-muted">{a.budget_used_pct}% used · {a.progress_pct}% done</p></>}
                  </td>
                  <td className="px-3 py-2.5 text-ink-muted">{manual ? "Manual entry" : `${a.expense_count} expense line${a.expense_count === 1 ? "" : "s"}`}</td>
                  <td className="px-3 py-2.5"><div className="flex flex-wrap gap-1">
                    {flags.length === 0 ? <span className={`px-2 py-0.5 rounded-full ${TONE.success}`}>OK</span>
                      : flags.map((f) => <span key={f} className={`px-2 py-0.5 rounded-full whitespace-nowrap ${TONE[FLAGS[f].tone]}`}>{FLAGS[f].label}</span>)}</div></td>
                  {canEdit && <td className="px-3 py-2.5 text-right whitespace-nowrap">
                    {!manual ? <span className="text-ink-muted" title="Edit the expense lines below">via expenses</span>
                      : isEd ? <><button onClick={save} disabled={actions.updateActivity.isPending} className="text-brand font-medium mr-2">Save</button><button onClick={() => { setEditing(null); setErr(""); }} className="text-ink-muted">Cancel</button></>
                      : <button onClick={() => setEditing({ id: a.id, est: String(Number(a.estimated_cost)), act: String(Number(a.actual_cost)) })} className="text-ink-muted hover:text-ink">Edit costs</button>}
                  </td>}
                </tr>
              );
            })}
            {pl.count > 0 && (
              <tr className="border-b border-line/60 bg-surface-2/40">
                <td className="px-3 py-2.5"><p className="font-medium text-ink">Project-level expenses</p><p className="text-ink-muted">Not tied to one activity (hosting, tools...)</p></td>
                <td className="px-3 py-2.5 text-right">{pkr(pl.estimated)}</td><td className="px-3 py-2.5 text-right">{pkr(pl.actual)}</td>
                <td className={`px-3 py-2.5 text-right ${num(pl.actual) > num(pl.estimated) ? "text-danger font-medium" : "text-ink-muted"}`}>{num(pl.actual) - num(pl.estimated) > 0 ? "+" : ""}{pkr(num(pl.actual) - num(pl.estimated))}</td>
                <td colSpan={canEdit ? 4 : 3} className="px-3 py-2.5 text-ink-muted">{pl.count} expense line{pl.count === 1 ? "" : "s"}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {err && <p className="text-xs text-danger">{err}</p>}
      <p className="text-[11px] text-ink-muted/80">An activity with expense lines takes its cost from those lines; otherwise from the manual figures. Nothing is counted twice.</p>
    </div>
  );
}
