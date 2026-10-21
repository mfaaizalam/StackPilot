import { TONE, num, pkr } from "../../utils/ganttFormat.js";

// Per-phase spend against the funding tagged to that phase.
export default function PhaseTable({ phases }) {
  if (!phases.length) return null;
  return (
    <div className="bg-surface border border-line rounded-card overflow-x-auto">
      <table className="w-full text-xs min-w-[640px]">
        <thead><tr className="text-left text-ink-muted/70 border-b border-line bg-surface-2/50">
          <th className="px-3 py-2 font-medium">Phase</th><th className="px-3 font-medium text-right">Estimated</th><th className="px-3 font-medium text-right">Actual</th>
          <th className="px-3 font-medium text-right">Variance</th><th className="px-3 font-medium text-right">Funding (committed / planned)</th><th className="px-3 font-medium">Status</th>
        </tr></thead>
        <tbody>
          {phases.map((p) => (
            <tr key={p.phase} className="border-b border-line/60">
              <td className="px-3 py-2 font-medium text-ink">{p.phase} <span className="text-ink-muted font-normal">({p.activity_count})</span></td>
              <td className="px-3 py-2 text-right">{pkr(p.estimated_cost)}</td><td className="px-3 py-2 text-right">{pkr(p.actual_cost)}</td>
              <td className={`px-3 py-2 text-right ${num(p.cost_variance) > 0 ? "text-danger font-medium" : "text-ink-muted"}`}>{num(p.cost_variance) > 0 ? "+" : ""}{pkr(p.cost_variance)}</td>
              <td className="px-3 py-2 text-right">{pkr(p.committed_funding)} / {pkr(p.planned_funding)}</td>
              <td className="px-3 py-2">{p.alerts.length === 0 ? <span className={`px-2 py-0.5 rounded-full ${TONE.success}`}>OK</span> : p.alerts.map((a) => (
                <span key={a} className={`px-2 py-0.5 rounded-full mr-1 whitespace-nowrap ${TONE.danger}`}>{a === "phase_overspent" ? "Spent more than funded" : "Over budget"}</span>))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
