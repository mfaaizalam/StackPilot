import { useMemo, useState } from "react";
import { fmtDate, fromDay, num, pkr, toDay } from "../../utils/ganttFormat.js";

const SCALES = { day: { px: 28, label: "Day" }, week: { px: 10, label: "Week" }, month: { px: 3.5, label: "Month" } };
const LABEL_W = 220, ROW_H = 40, HEAD_H = 40, BAR_H = 20;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function buildTicks(min, max, scale, px) {
  const ticks = [];
  for (let d = min; d <= max; d++) {
    const dt = fromDay(d);
    const dom = dt.getUTCDate();
    if (scale === "day") ticks.push({ x: (d - min) * px, label: dom === 1 ? `${dom} ${MONTHS[dt.getUTCMonth()]}` : String(dom) });
    else if (scale === "week" && dt.getUTCDay() === 1) ticks.push({ x: (d - min) * px, label: `${dom} ${MONTHS[dt.getUTCMonth()]}` });
    else if (scale === "month" && dom === 1) ticks.push({ x: (d - min) * px, label: `${MONTHS[dt.getUTCMonth()]} ${String(dt.getUTCFullYear()).slice(2)}` });
  }
  return ticks;
}

export default function GanttChart({ activities, today }) {
  const [scale, setScale] = useState("week");
  const px = SCALES[scale].px;

  const geo = useMemo(() => {
    if (!activities.length) return null;
    const starts = activities.map((a) => toDay(a.start_date));
    const ends = activities.map((a) => toDay(a.end_date));
    const min = Math.min(...starts) - 2;
    const max = Math.max(...ends) + 2;
    const rowOf = new Map(activities.map((a, i) => [a.id, i]));
    return { min, max, total: max - min + 1, rowOf };
  }, [activities]);

  if (!geo) {
    return <p className="text-sm text-ink-muted bg-surface border border-dashed border-ink-muted/40 rounded-card px-4 py-10 text-center">
      No activities yet. Generate them from your Kanban board, or add one below.</p>;
  }

  const { min, total, rowOf } = geo;
  const chartW = Math.max(total * px, 320);
  const ticks = buildTicks(min, geo.max, scale, px);
  const todayX = (toDay(today) - min) * px;
  const xStart = (a) => (toDay(a.start_date) - min) * px;
  const xEnd = (a) => (toDay(a.end_date) - min + 1) * px;
  const yMid = (i) => i * ROW_H + ROW_H / 2;

  const arrows = [];
  activities.forEach((a, i) => {
    (a.depends_on || []).forEach((dep) => {
      const j = rowOf.get(dep);
      if (j === undefined) return;
      const x1 = xEnd(activities[j]), y1 = yMid(j), x2 = xStart(a), y2 = yMid(i);
      const bad = (a.conflicting_dependencies || []).includes(dep);
      const dir = y2 > y1 ? 1 : -1;
      const d = x2 >= x1 + 12
        ? `M${x1},${y1} H${x1 + 6} V${y2} H${x2 - 1}`
        : `M${x1},${y1} H${x1 + 6} V${y1 + dir * (ROW_H / 2)} H${x2 - 8} V${y2} H${x2 - 1}`;
      arrows.push({ key: `${dep}-${a.id}`, d, bad });
    });
  });

  return (
    <div className="bg-surface border border-line rounded-card">
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-line">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink-muted">
          <span className="flex items-center gap-1.5"><i className="inline-block w-3 h-2.5 rounded-sm bg-brand" /> progress</span>
          <span className="flex items-center gap-1.5"><i className="inline-block w-3 h-2.5 rounded-sm ring-2 ring-danger" /> over budget / hours</span>
          <span className="flex items-center gap-1.5"><i className="inline-block w-3 h-2.5 rounded-sm ring-2 ring-warning" /> behind schedule</span>
          <span className="flex items-center gap-1.5"><i className="inline-block w-0.5 h-3 bg-danger" /> today</span>
        </div>
        <div className="flex rounded-lg border border-line overflow-hidden shrink-0" role="group" aria-label="Time scale">
          {Object.entries(SCALES).map(([k, v]) => (
            <button key={k} onClick={() => setScale(k)} aria-pressed={scale === k}
              className={`text-xs px-3 py-1.5 transition ${scale === k ? "bg-brand text-brand-fg" : "bg-surface text-ink-muted hover:bg-surface-2"}`}>
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* The chart scrolls inside this box so the page itself never overflows on a phone */}
      <div className="overflow-x-auto">
        <div style={{ width: LABEL_W + chartW }}>
          <div className="flex border-b border-line" style={{ height: HEAD_H }}>
            <div className="sticky left-0 z-20 bg-surface border-r border-line px-3 flex items-center text-[11px] uppercase tracking-wide text-ink-muted/70 shrink-0" style={{ width: LABEL_W }}>Activity</div>
            <div className="relative shrink-0" style={{ width: chartW }}>
              {ticks.map((t, i) => (
                <span key={i} className="absolute top-0 h-full border-l border-line pl-1 pt-2.5 text-[10px] text-ink-muted whitespace-nowrap" style={{ left: t.x }}>{t.label}</span>
              ))}
            </div>
          </div>

          <div className="relative">
            {activities.map((a, i) => {
              const flags = a.flags || [];
              const red = flags.includes("cost_overrun") || flags.includes("time_overrun");
              const amber = !red && (flags.includes("behind_schedule") || flags.includes("overdue"));
              const w = Math.max((a.duration_days) * px, 6);
              return (
                <div key={a.id} className={`flex border-b border-line/60 ${i % 2 ? "bg-surface-2/40" : ""}`} style={{ height: ROW_H }}>
                  <div className="sticky left-0 z-10 bg-surface border-r border-line px-3 flex flex-col justify-center shrink-0 min-w-0" style={{ width: LABEL_W }}>
                    <span className="text-xs font-medium text-ink truncate" title={a.name}>{a.name}</span>
                    <span className="text-[10px] text-ink-muted truncate">{a.phase || "No phase"} · {a.duration_days}d · {a.progress_pct}%</span>
                  </div>
                  <div className="relative shrink-0" style={{ width: chartW }}>
                    <div
                      className={`absolute rounded-md bg-brand/20 overflow-hidden ${red ? "ring-2 ring-danger" : amber ? "ring-2 ring-warning" : ""}`}
                      style={{ left: xStart(a), width: w, top: (ROW_H - BAR_H) / 2, height: BAR_H }}
                      title={`${a.name}\n${fmtDate(a.start_date)} to ${fmtDate(a.end_date)} (${a.duration_days} days)\nProgress ${a.progress_pct}%\nEstimated ${pkr(a.estimated_cost)}, actual ${pkr(a.actual_cost)}\nHours ${num(a.actual_hours)} of ${num(a.planned_hours)}`}
                    >
                      <div className="h-full bg-brand" style={{ width: `${a.progress_pct}%` }} />
                    </div>
                  </div>
                </div>
              );
            })}

            {/* gridlines, dependency arrows and the today line sit above the rows */}
            <svg className="absolute pointer-events-none" style={{ left: LABEL_W, top: 0 }} width={chartW} height={activities.length * ROW_H} aria-hidden="true">
              <defs>
                <marker id="gantt-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="currentColor" /></marker>
              </defs>
              {arrows.map((ar) => (
                <path key={ar.key} d={ar.d} fill="none" strokeWidth="1.3" markerEnd="url(#gantt-arrow)"
                  className={ar.bad ? "text-danger" : "text-ink-muted"} stroke="currentColor" />
              ))}
              {todayX >= 0 && todayX <= chartW && <line x1={todayX} x2={todayX} y1="0" y2={activities.length * ROW_H} className="text-danger" stroke="currentColor" strokeWidth="1.5" />}
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
