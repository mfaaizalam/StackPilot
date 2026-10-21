// Shared helpers for the Gantt / finance screens (Issue #9).
const nf = new Intl.NumberFormat("en-PK", { maximumFractionDigits: 0 });

// Money arrives from the API as strings ("12500.50") to avoid float drift; format only at display time.
export const pkr = (v) => {
  const n = Number(v ?? 0);
  return `${n < 0 ? "-" : ""}PKR ${nf.format(Math.abs(n))}`;
};
export const num = (v) => Number(v ?? 0);

// Dates are ISO "YYYY-MM-DD". Work in whole UTC days so time zones can never shift a bar.
export const toDay = (s) => Math.floor(Date.parse(`${s}T00:00:00Z`) / 86400000);
export const fromDay = (n) => new Date(n * 86400000);
export const fmtDate = (s) =>
  s ? new Date(`${s}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "-";

export const errText = (e, fallback = "Something went wrong. Please try again.") => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg.replace(/^Value error, /, "");
  return fallback;
};

export const FLAGS = {
  cost_overrun: { label: "Over budget", tone: "danger" },
  unbudgeted_cost: { label: "No budget set", tone: "warning" },
  time_overrun: { label: "Over hours", tone: "danger" },
  behind_schedule: { label: "Behind schedule", tone: "warning" },
  overdue: { label: "Overdue", tone: "danger" },
  burning_faster_than_progress: { label: "Spending ahead of progress", tone: "warning" },
  dependency_conflict: { label: "Starts before a dependency ends", tone: "warning" },
};

export const TONE = {
  danger: "text-danger bg-danger-soft",
  warning: "text-warning bg-warning-soft",
  success: "text-success bg-success-soft",
  muted: "text-ink-muted bg-surface-2",
};

export const alertText = (a) => {
  const m = pkr(a.amount);
  switch (a.code) {
    case "insufficient_funds": return `Insufficient funds: actual costs are ${m} more than the money received so far (base budget + disbursed increments).`;
    case "over_committed_budget": return `Over budget: actual costs are ${m} more than the committed budget (base + approved + disbursed).`;
    case "estimate_exceeds_forecast": return `The estimated cost of all activities is ${m} more than even the forecast budget (planned increments included).`;
    case "estimate_exceeds_committed": return `Estimated costs are ${m} above the committed budget. The gap depends on planned increments being approved.`;
    case "funds_running_low": return `Funds are running low: only ${m} of available funds remain.`;
    default: return a.code;
  }
};

export const STATUS_STYLE = {
  planned: "bg-surface-2 text-ink-muted border-line",
  approved: "bg-info/10 text-info border-info/30",
  disbursed: "bg-success-soft text-success border-success/30",
};
