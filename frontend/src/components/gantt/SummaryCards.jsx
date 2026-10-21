import { num, pkr } from "../../utils/ganttFormat.js";

const RING = { danger: "border-danger/40", warning: "border-warning/40", success: "border-success/30", none: "border-line" };
const TEXT = { danger: "text-danger", warning: "text-warning", success: "text-success", none: "text-ink" };

function Card({ label, value, sub, tone = "none" }) {
  return (
    <div className={`card-gradient border ${RING[tone]} rounded-card p-4`}>
      <p className="text-[11px] uppercase tracking-wide text-ink-muted/70">{label}</p>
      <p className={`text-lg sm:text-xl font-semibold mt-1 ${TEXT[tone]}`}>{value}</p>
      {sub && <p className="text-xs text-ink-muted mt-0.5">{sub}</p>}
    </div>
  );
}

export default function SummaryCards({ summary: s, project: p }) {
  const remaining = num(s.remaining_funds);
  const remTone = remaining < 0 ? "danger" : remaining < num(s.available_funds) * 0.1 ? "warning" : "success";
  const overEst = num(s.actual_total) > num(s.estimated_total) && num(s.estimated_total) > 0;
  const variance = num(s.cost_variance);
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Card label="Estimated cost" value={pkr(s.estimated_total)} sub={`${p.activity_count} activities`} />
        <Card label="Actual cost" value={pkr(s.actual_total)} tone={overEst ? "danger" : "none"}
          sub={variance ? `${variance > 0 ? "+" : ""}${pkr(variance)} vs estimate` : "on estimate"} />
        <Card label="Committed budget" value={pkr(s.committed_budget)}
          tone={num(s.actual_total) > num(s.committed_budget) ? "danger" : "none"}
          sub={`Forecast ${pkr(s.forecast_budget)}`} />
        <Card label="Available funds" value={pkr(s.available_funds)}
          sub={num(s.awaiting_disbursement) > 0 ? `${pkr(s.awaiting_disbursement)} approved, not yet received` : "Base + disbursed"} />
        <Card label="Remaining funds" value={pkr(remaining)} tone={remTone} sub="Available minus actual cost" />
      </div>
      {p.activity_count > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs text-ink-muted">
          <p className="bg-surface-2 rounded-lg px-3 py-2">Progress <b className="text-ink">{p.progress_pct}%</b> vs time elapsed <b className="text-ink">{p.elapsed_pct}%</b></p>
          <p className="bg-surface-2 rounded-lg px-3 py-2">Duration <b className="text-ink">{p.duration_days} days</b></p>
          <p className="bg-surface-2 rounded-lg px-3 py-2">Hours planned <b className="text-ink">{num(p.planned_hours)}</b></p>
          <p className={`rounded-lg px-3 py-2 ${num(p.actual_hours) > num(p.planned_hours) && num(p.planned_hours) > 0 ? "bg-danger-soft text-danger" : "bg-surface-2"}`}>
            Hours actual <b>{num(p.actual_hours)}</b>
          </p>
        </div>
      )}
    </div>
  );
}
