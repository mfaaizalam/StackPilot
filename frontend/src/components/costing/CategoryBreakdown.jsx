import { TONE, num, pkr } from "../../utils/ganttFormat.js";

// Where the money goes: estimated vs actual per expense category. Rows always add up to the project total.
export default function CategoryBreakdown({ categories }) {
  if (!categories.length) {
    return <p className="text-sm text-ink-muted bg-surface border border-dashed border-ink-muted/40 rounded-card px-4 py-8 text-center">
      No costs yet. Add an expense below, or generate activities with costs from the Kanban board.</p>;
  }
  const totalEst = categories.reduce((t, c) => t + num(c.estimated), 0);
  const totalAct = categories.reduce((t, c) => t + num(c.actual), 0);
  return (
    <div className="bg-surface border border-line rounded-card overflow-x-auto">
      <table className="w-full text-xs min-w-[640px]">
        <thead><tr className="text-left text-ink-muted/70 border-b border-line bg-surface-2/50">
          <th className="px-3 py-2 font-medium">Category</th><th className="px-3 font-medium text-right">Estimated</th>
          <th className="px-3 font-medium text-right">Actual</th><th className="px-3 font-medium text-right">Variance</th>
          <th className="px-3 font-medium w-40">Share of total</th><th className="px-3 font-medium">Status</th>
        </tr></thead>
        <tbody>
          {categories.map((c) => (
            <tr key={c.category} className="border-b border-line/60">
              <td className="px-3 py-2.5 font-medium text-ink">{c.label}</td>
              <td className="px-3 py-2.5 text-right whitespace-nowrap">{pkr(c.estimated)}</td>
              <td className="px-3 py-2.5 text-right whitespace-nowrap">{pkr(c.actual)}</td>
              <td className={`px-3 py-2.5 text-right whitespace-nowrap ${c.overrun ? "text-danger font-medium" : "text-ink-muted"}`}>
                {num(c.variance) > 0 ? "+" : ""}{pkr(c.variance)}{c.variance_pct !== null && <span className="block">{c.variance_pct}%</span>}</td>
              <td className="px-3 py-2.5">
                <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden"><div className={`h-full ${c.overrun ? "bg-danger" : "bg-brand"}`} style={{ width: `${Math.min(c.share_pct, 100)}%` }} /></div>
                <p className="mt-1 text-ink-muted">{c.share_pct}%</p>
              </td>
              <td className="px-3 py-2.5">{c.overrun ? <span className={`px-2 py-0.5 rounded-full ${TONE.danger}`}>Over estimate</span> : <span className={`px-2 py-0.5 rounded-full ${TONE.success}`}>Within estimate</span>}</td>
            </tr>
          ))}
          <tr className="bg-surface-2/50 font-semibold text-ink">
            <td className="px-3 py-2.5">Total</td><td className="px-3 py-2.5 text-right">{pkr(totalEst)}</td>
            <td className="px-3 py-2.5 text-right">{pkr(totalAct)}</td>
            <td className={`px-3 py-2.5 text-right ${totalAct > totalEst && totalEst > 0 ? "text-danger" : ""}`}>{totalAct - totalEst > 0 ? "+" : ""}{pkr(totalAct - totalEst)}</td><td colSpan={2} />
          </tr>
        </tbody>
      </table>
    </div>
  );
}
