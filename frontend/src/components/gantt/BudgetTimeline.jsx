import { fmtDate, num, pkr, toDay } from "../../utils/ganttFormat.js";

const DOT = { planned: "text-ink-muted", approved: "text-info", disbursed: "text-success" };

// Cumulative project budget after each finance increment, as a step chart (inline SVG, no library).
export default function BudgetTimeline({ summary: s, project: p, today }) {
  const tl = s.timeline;
  if (!tl.length) {
    return <p className="text-sm text-ink-muted">Add finance increments to see how the budget grows over time.</p>;
  }
  const base = num(s.base_budget);
  const dates = [...tl.map((t) => toDay(t.date)), toDay(today), ...(p.start_date ? [toDay(p.start_date)] : []), ...(p.end_date ? [toDay(p.end_date)] : [])];
  const x0 = Math.min(...dates), x1 = Math.max(...dates, x0 + 1);
  const yMax = Math.max(num(s.forecast_budget), num(s.actual_total), base, 1) * 1.12;
  const W = 720, H = 240, L = 78, R = 16, T = 14, B = 30;
  const X = (d) => L + ((d - x0) / (x1 - x0)) * (W - L - R);
  const Y = (v) => T + (1 - v / yMax) * (H - T - B);

  const step = (key) => {
    let d = `M${X(x0)},${Y(base)}`, prev = base;
    tl.forEach((t) => { const x = X(toDay(t.date)), v = num(t[key]); d += ` H${x} V${Y(v)}`; prev = v; });
    return d + ` H${X(x1)}`;
  };
  const gridVals = [0, 0.25, 0.5, 0.75, 1].map((f) => yMax * f / 1.12);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
        aria-label={`Cumulative budget grows from ${pkr(base)} to ${pkr(s.forecast_budget)} across ${tl.length} increments`}>
        {gridVals.map((v, i) => (
          <g key={i}>
            <line x1={L} x2={W - R} y1={Y(v)} y2={Y(v)} className="text-line" stroke="currentColor" />
            <text x={L - 6} y={Y(v) + 3} textAnchor="end" fontSize="10" className="fill-current text-ink-muted">{v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${Math.round(v / 1e3)}k` : Math.round(v)}</text>
          </g>
        ))}
        <path d={step("cumulative_budget")} fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="5 4" className="text-ink-muted" />
        <path d={step("cumulative_committed")} fill="none" stroke="currentColor" strokeWidth="2.5" className="text-brand" />
        <line x1={L} x2={W - R} y1={Y(num(s.actual_total))} y2={Y(num(s.actual_total))} stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 3" className="text-danger" />
        <text x={W - R} y={Y(num(s.actual_total)) - 4} textAnchor="end" fontSize="10" className="fill-current text-danger">Actual cost {pkr(s.actual_total)}</text>
        {tl.map((t) => <circle key={t.id} cx={X(toDay(t.date))} cy={Y(num(t.cumulative_budget))} r="4" fill="currentColor" className={DOT[t.status]} />)}
        <text x={L} y={H - 8} fontSize="10" className="fill-current text-ink-muted">{fmtDate(new Date(x0 * 86400000).toISOString().slice(0, 10))}</text>
        <text x={W - R} y={H - 8} textAnchor="end" fontSize="10" className="fill-current text-ink-muted">{fmtDate(new Date(x1 * 86400000).toISOString().slice(0, 10))}</text>
      </svg>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-ink-muted mb-3">
        <span><i className="inline-block w-4 h-0.5 bg-brand align-middle mr-1" />Committed (base + approved + disbursed)</span>
        <span><i className="inline-block w-4 border-t-2 border-dashed border-ink-muted align-middle mr-1" />Forecast (incl. planned)</span>
        <span><i className="inline-block w-4 border-t-2 border-dotted border-danger align-middle mr-1" />Actual cost</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="text-left text-ink-muted/70 border-b border-line">
            <th className="py-1.5 pr-3 font-medium">Date</th><th className="pr-3 font-medium">Status</th>
            <th className="pr-3 font-medium text-right">Increment</th><th className="pr-3 font-medium text-right">Committed after</th><th className="font-medium text-right">Forecast after</th>
          </tr></thead>
          <tbody>
            <tr className="border-b border-line/60"><td className="py-1.5 pr-3">Start</td><td className="pr-3">base budget</td><td className="pr-3 text-right">-</td><td className="pr-3 text-right">{pkr(base)}</td><td className="text-right">{pkr(base)}</td></tr>
            {tl.map((t) => (
              <tr key={t.id} className="border-b border-line/60">
                <td className="py-1.5 pr-3">{fmtDate(t.date)}</td><td className="pr-3 capitalize">{t.status}</td>
                <td className="pr-3 text-right">+{pkr(t.amount)}</td><td className="pr-3 text-right">{pkr(t.cumulative_committed)}</td><td className="text-right font-medium">{pkr(t.cumulative_budget)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
