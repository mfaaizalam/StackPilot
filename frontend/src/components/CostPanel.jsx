import { useState, useEffect, useCallback } from "react";
import api from "../api/axios.js";

const errText = (e, fallback = "Something went wrong. Please try again.") => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  return fallback;
};

const pkr = (n) => `PKR ${Math.round(n ?? 0).toLocaleString("en-US")}`;
const short = (n) => {
  const v = Math.abs(n);
  const s = v >= 1e7 ? `${(v / 1e7).toFixed(2)} crore` : v >= 1e5 ? `${(v / 1e5).toFixed(1)} lakh` : Math.round(v).toLocaleString("en-US");
  return `${n < 0 ? "-" : ""}PKR ${s}`;
};

const GROUPS = [
  ["labour", "Labour", "bg-brand"],
  ["overhead", "Overheads", "bg-ink-muted/60"],
  ["infrastructure", "Hosting, tools and setup", "bg-ink-muted/35"],
  ["contingency", "Contingency", "bg-warning"],
  ["tax", "Tax", "bg-ink-muted/20"],
];

const LEVELS = [["low", "Low"], ["nominal", "Normal"], ["high", "High"]];
const PLATFORMS = [["web", "Web app"], ["mobile", "Mobile app"], ["web_mobile", "Web + mobile"], ["desktop", "Desktop"]];

const inputCls = "w-full text-sm text-ink border border-line rounded-lg px-3 py-2 bg-surface focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-ink-muted/60";

function Select({ label, value, onChange, options, hint }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-ink mb-1">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={inputCls}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      {hint && <span className="block text-[11px] text-ink-muted/70 mt-1">{hint}</span>}
    </label>
  );
}

function Tile({ label, value, sub }) {
  return (
    <div className="card-gradient border border-line rounded-card p-4">
      <p className="text-[11px] uppercase tracking-wide text-ink-muted/70">{label}</p>
      <p className="text-xl font-semibold text-ink mt-1">{value}</p>
      {sub && <p className="text-xs text-ink-muted mt-0.5">{sub}</p>}
    </div>
  );
}

/* Optimistic ── expected ── pessimistic range, drawn as inline SVG */
function RangeChart({ low, mid, high }) {
  const W = 640, pad = 70, y = 52;
  const span = Math.max(high - low, 1);
  const x = (v) => pad + ((v - low) / span) * (W - 2 * pad);
  return (
    <svg viewBox={`0 0 ${W} 110`} className="w-full" role="img"
      aria-label={`Cost range from ${pkr(low)} to ${pkr(high)}, expected ${pkr(mid)}`}>
      <line x1={x(low)} x2={x(high)} y1={y} y2={y} className="stroke-ink-muted/25" strokeWidth="10" strokeLinecap="round" />
      <line x1={x(low)} x2={x(mid)} y1={y} y2={y} className="stroke-ink-muted/60" strokeWidth="10" strokeLinecap="round" />
      <circle cx={x(low)} cy={y} r="6" className="fill-surface stroke-ink-muted" strokeWidth="2" />
      <circle cx={x(high)} cy={y} r="6" className="fill-surface stroke-ink-muted" strokeWidth="2" />
      <circle cx={x(mid)} cy={y} r="9" className="fill-brand stroke-surface" strokeWidth="3" />
      <text x={x(mid)} y={y - 20} textAnchor="middle" className="fill-ink text-[13px] font-semibold">{short(mid)}</text>
      <text x={x(mid)} y={y - 34} textAnchor="middle" className="fill-ink-muted/70 text-[10px]">EXPECTED (PERT)</text>
      <text x={x(low)} y={y + 28} textAnchor="start" className="fill-ink-muted text-[12px]">{short(low)}</text>
      <text x={x(low)} y={y + 42} textAnchor="start" className="fill-ink-muted/70 text-[10px]">OPTIMISTIC</text>
      <text x={x(high)} y={y + 28} textAnchor="end" className="fill-ink-muted text-[12px]">{short(high)}</text>
      <text x={x(high)} y={y + 42} textAnchor="end" className="fill-ink-muted/70 text-[10px]">PESSIMISTIC</text>
    </svg>
  );
}

function GroupBar({ groups, total }) {
  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden bg-surface-2">
        {GROUPS.map(([k, , c]) => groups[k] > 0 && <div key={k} className={c} style={{ width: `${(groups[k] / total) * 100}%` }} title={`${k}: ${pkr(groups[k])}`} />)}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
        {GROUPS.map(([k, label, c]) => groups[k] > 0 && (
          <span key={k} className="text-xs text-ink-muted flex items-center gap-1.5">
            <span className={`inline-block w-2.5 h-2.5 rounded-sm ${c}`} />{label} {Math.round((groups[k] / total) * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}

function Section({ title, children, right }) {
  return (
    <section className="bg-surface border border-line rounded-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>{right}
      </div>
      {children}
    </section>
  );
}

export default function CostPanel({ boardId, srsId, version }) {
  const base = `/boards/${boardId}/srs/cost`;
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);          // saved estimate row
  const [form, setForm] = useState({ platform: "web", complexity: "nominal", reliability: "nominal", team_experience: "nominal", revenue: "", horizon: 3 });
  const [busy, setBusy] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [rates, setRates] = useState(null);
  const [showRates, setShowRates] = useState(false);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const load = useCallback(async () => {
    try {
      const { data: d } = await api.get(`${base}/`);
      setData(d);
      const i = d.result?.inputs;
      if (i) setForm({ platform: i.platform, complexity: i.complexity, reliability: i.reliability, team_experience: i.team_experience,
        revenue: i.expected_annual_revenue ?? "", horizon: i.horizon_years });
    } catch (e) { if (e?.response?.status !== 404) setError(errText(e)); }
    setLoading(false);
  }, [base]);
  useEffect(() => { load(); }, [load]);

  const calculate = async () => {
    setBusy(true); setError(""); setNotice("");
    try {
      const rev = form.revenue === "" ? null : Number(form.revenue);
      if (rev !== null && (Number.isNaN(rev) || rev < 0)) { setError("Expected yearly revenue must be a positive number."); setBusy(false); return; }
      const { data: d } = await api.post(`${base}/estimate`, {
        platform: form.platform, complexity: form.complexity, reliability: form.reliability,
        team_experience: form.team_experience, expected_annual_revenue: rev, horizon_years: Number(form.horizon) || 3,
      });
      setData(d);
    } catch (e) { setError(errText(e)); }
    setBusy(false);
  };

  const explain = async () => {
    setExplaining(true); setError(""); setNotice("");
    try {
      const { data: d } = await api.post(`${base}/${data.id}/explain`);
      setData(d); if (d.notice) setNotice(d.notice);
    } catch (e) { setError(errText(e)); }
    setExplaining(false);
  };

  const toggleRates = async () => {
    setShowRates((s) => !s);
    if (!rates) { try { const { data: r } = await api.get(`${base}/rates`); setRates(r); } catch (e) { setError(errText(e)); } }
  };

  if (loading) return <div className="h-40 bg-surface border border-line rounded-card animate-pulse" />;

  const r = data?.result;
  const outdated = data && (data.srs_outdated || data.srs_id !== srsId);
  const roiOn = form.revenue !== "" && Number(form.revenue) > 0;

  return (
    <div className="space-y-6">
      <Section title="Estimate settings">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Select label="Platform" value={form.platform} onChange={set("platform")} options={PLATFORMS} />
          <Select label="Project complexity" value={form.complexity} onChange={set("complexity")} options={LEVELS} hint="Hard algorithms, many integrations = High" />
          <Select label="Reliability needed" value={form.reliability} onChange={set("reliability")} options={LEVELS} hint="Payments or health data = High" />
          <Select label="Team experience" value={form.team_experience} onChange={set("team_experience")} options={LEVELS} hint="Beginners = Low" />
          <label className="block col-span-2">
            <span className="block text-xs font-medium text-ink mb-1">Expected yearly revenue in PKR (optional)</span>
            <input type="number" min="0" value={form.revenue} onChange={(e) => set("revenue")(e.target.value)} placeholder="e.g. 12000000"
              className={`${inputCls} placeholder:text-ink-muted/60`} />
            <span className="block text-[11px] text-ink-muted/70 mt-1">Adds payback and ROI. Your own expectation, not a forecast.</span>
          </label>
          <label className="block">
            <span className="block text-xs font-medium text-ink mb-1">ROI horizon (years)</span>
            <input type="number" min="1" max="10" value={form.horizon} onChange={(e) => set("horizon")(e.target.value)} disabled={!roiOn}
              className={`${inputCls} disabled:bg-surface-2 disabled:opacity-60`} />
          </label>
          <div className="flex items-end">
            <button onClick={calculate} disabled={busy}
              className="w-full text-sm font-medium px-4 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover disabled:opacity-50 transition">
              {busy ? "Calculating…" : r ? "Recalculate" : "Calculate cost"}
            </button>
          </div>
        </div>
        <p className="text-xs text-ink-muted/70 mt-3">Calculated from SRS version {version} using a fixed rate table. No AI is involved in the numbers, so the same settings always give the same result.</p>
        {error && <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-lg px-3 py-2 mt-3">{error}</p>}
      </Section>

      {r && (
        <>
          {outdated && (
            <p className="text-sm text-warning bg-warning-soft border border-warning/20 rounded-card px-4 py-3">
              This estimate was made from SRS version {data.srs_version}, but the current version is {version}. Press Recalculate to update it.
            </p>
          )}
          {r.rates_meta.unverified_items.length > 0 && (
            <p className="text-sm text-warning bg-warning-soft border border-warning/20 rounded-card px-4 py-3">
              {r.rates_meta.unverified_items.length} rates in the table are still unverified placeholders, so treat these figures as indicative until they are checked against current local data.
            </p>
          )}

          <Section title="Expected cost">
            <RangeChart low={r.pert.low} mid={r.pert.total} high={r.pert.high} />
            <p className="text-xs text-ink-muted mt-2">Expected = (optimistic + 4 × likely + pessimistic) / 6. Rates last updated {r.rates_meta.last_updated}.</p>
          </Section>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Tile label="Duration" value={`${r.effort.duration_months} months`} sub={`${r.effort.person_months} person-months`} />
            <Tile label="Average team" value={`${r.effort.team_size} ${r.effort.team_size === 1 ? "person" : "people"}`} sub={`${r.size.ufp} function points`} />
            <Tile label="Monthly spend" value={short(r.monthly_burn)} sub="average over the project" />
            <Tile label="Total (PKR)" value={pkr(r.pert.total)} sub="expected, incl. tax" />
          </div>

          <Section title="Where the money goes">
            <GroupBar groups={r.pert.groups} total={r.pert.total || 1} />
            <div className="overflow-x-auto mt-5">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-ink-muted/70 border-b border-line">
                  <th className="py-2 font-medium">Role</th><th className="py-2 font-medium text-right">Share</th>
                  <th className="py-2 font-medium text-right">Person-months</th><th className="py-2 font-medium text-right hidden sm:table-cell">Monthly salary</th>
                  <th className="py-2 font-medium text-right">Cost</th></tr></thead>
                <tbody>
                  {r.roles.map((x) => (
                    <tr key={x.id} className="border-b border-line">
                      <td className="py-2 text-ink">{x.label}</td>
                      <td className="py-2 text-right text-ink-muted">{Math.round(x.share * 100)}%</td>
                      <td className="py-2 text-right text-ink-muted">{x.person_months}</td>
                      <td className="py-2 text-right text-ink-muted hidden sm:table-cell">{x.monthly_salary_min.toLocaleString("en-US")} – {x.monthly_salary_max.toLocaleString("en-US")}</td>
                      <td className="py-2 text-right font-medium text-ink">{pkr(x.cost)}</td>
                    </tr>
                  ))}
                  {r.pert.lines.filter((l) => l.group !== "labour").map((l) => (
                    <tr key={l.key} className="border-b border-line">
                      <td className="py-2 text-ink-muted" colSpan={4}>{l.label}</td>
                      <td className="py-2 text-right text-ink">{pkr(l.amount)}</td>
                    </tr>
                  ))}
                  <tr><td className="py-3 font-semibold text-ink" colSpan={4}>Total (expected)</td>
                    <td className="py-3 text-right font-semibold text-ink">{pkr(r.pert.total)}</td></tr>
                </tbody>
              </table>
            </div>
          </Section>

          <Section title="Three scenarios">
            <div className="grid sm:grid-cols-3 gap-4">
              {["optimistic", "likely", "pessimistic"].map((k) => {
                const s = r.scenarios[k];
                return (
                  <div key={k} className="border border-line bg-surface-2 rounded-card p-4">
                    <p className="text-xs text-ink-muted/70 uppercase tracking-wide">{s.label}</p>
                    <p className="text-lg font-semibold text-ink mt-1">{pkr(s.total)}</p>
                    <p className="text-xs text-ink-muted mt-1">{s.duration_months} months · {s.person_months} person-months · team of {s.team_size}</p>
                  </div>
                );
              })}
            </div>
          </Section>

          <Section title="What if? (sensitivity)">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-ink-muted/70 border-b border-line">
                  <th className="py-2 font-medium">Change</th><th className="py-2 font-medium text-right">Expected cost</th><th className="py-2 font-medium text-right">Difference</th></tr></thead>
                <tbody>
                  {r.sensitivity.map((s) => (
                    <tr key={s.label} className="border-b border-line">
                      <td className="py-2 text-ink">{s.label}</td>
                      <td className="py-2 text-right text-ink">{pkr(s.total)}</td>
                      <td className={`py-2 text-right font-medium ${s.delta_pct > 0 ? "text-danger" : s.delta_pct < 0 ? "text-success" : "text-ink-muted/70"}`}>
                        {s.delta_pct > 0 ? "+" : ""}{s.delta_pct}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-ink-muted/70 mt-3">Scope changes cost more than their size because larger projects need disproportionately more coordination.</p>
          </Section>

          {r.roi && (
            <Section title="Return on investment">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Tile label="Yearly revenue" value={short(r.roi.expected_annual_revenue)} sub="your expectation" />
                <Tile label="Yearly running cost" value={short(r.roi.annual_running_cost)} sub="hosting, support, upkeep" />
                <Tile label="Payback" value={r.roi.payback_months == null ? "Never" : `${r.roi.payback_months} months`}
                  sub={r.roi.payback_months == null ? "" : `${r.roi.payback_months_best}–${r.roi.payback_months_worst} months range`} />
                <Tile label={`ROI over ${r.roi.horizon_years} yr`} value={r.roi.roi_pct == null ? "–" : `${r.roi.roi_pct}%`}
                  sub={r.roi.break_even_month_from_start == null ? "" : `break-even in month ${r.roi.break_even_month_from_start}`} />
              </div>
              <div className="flex flex-wrap gap-3 mt-4">
                {r.roi.cumulative.map((c) => (
                  <span key={c.year} className={`text-xs rounded-lg px-3 py-1.5 border ${c.net_position >= 0 ? "bg-success-soft border-success/20 text-success" : "bg-danger-soft border-danger/20 text-danger"}`}>
                    Year {c.year}: {short(c.net_position)}
                  </span>
                ))}
              </div>
              <p className="text-xs text-ink-muted/70 mt-3">{r.roi.note}</p>
            </Section>
          )}

          <Section title="Explanation" right={
            <button onClick={explain} disabled={explaining}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-line text-ink hover:bg-surface-2 disabled:opacity-50 transition">
              {explaining ? "Writing…" : data.explanation_source === "ai" ? "Rewrite with AI" : "Explain with AI"}
            </button>}>
            {data.explanation && (
              <div className="space-y-4 text-sm text-ink">
                <p className="leading-relaxed">{data.explanation.summary}</p>
                {[["What drives the cost", "key_drivers"], ["Risks", "risks"], ["Ways to reduce cost", "tips"]].map(([t, k]) => (
                  data.explanation[k]?.length > 0 && (
                    <div key={k}>
                      <p className="text-xs font-semibold text-ink mb-1">{t}</p>
                      <ul className="list-disc pl-5 space-y-1">{data.explanation[k].map((x, i) => <li key={i}>{x}</li>)}</ul>
                    </div>
                  )
                ))}
              </div>
            )}
            <p className="text-xs text-ink-muted/70 mt-4">
              {data.explanation_source === "ai" ? "Written by AI from the calculated figures only; every number was checked against the calculation."
                : "Standard explanation built from the calculated figures."}
            </p>
            {notice && <p className="text-xs text-warning mt-2">{notice}</p>}
          </Section>

          <Section title="Assumptions and checks">
            <ul className="list-disc pl-5 space-y-1.5 text-sm text-ink">{r.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
            <div className="mt-4 text-xs text-ink-muted space-y-1">
              <p>Cross-check (use case points): {r.cross_checks.use_case_points.ucp} points ≈ {r.cross_checks.use_case_points.person_months} person-months, which {r.cross_checks.use_case_points.agreement === "close" ? "is close to" : "differs noticeably from"} the main model.</p>
              {r.cross_checks.board_points && <p>Your Kanban board holds {r.cross_checks.board_points.total_points} story points across {r.cross_checks.board_points.tasks} tasks. {r.cross_checks.board_points.note}</p>}
            </div>
            <button onClick={toggleRates} className="mt-4 text-xs font-medium text-ink underline underline-offset-2">{showRates ? "Hide" : "Show"} the rate table</button>
            {showRates && rates && (
              <div className="overflow-x-auto mt-3">
                <table className="w-full text-xs">
                  <thead><tr className="text-left text-ink-muted/70 border-b border-line"><th className="py-1.5 font-medium">Item</th><th className="py-1.5 font-medium">Value</th><th className="py-1.5 font-medium">Status</th><th className="py-1.5 font-medium hidden sm:table-cell">Source</th></tr></thead>
                  <tbody>
                    {Object.values(rates.roles).map((x) => <RateRow key={x.label} name={`${x.label} (per month)`} value={`${x.monthly_min.toLocaleString("en-US")} – ${x.monthly_max.toLocaleString("en-US")}`} it={x} />)}
                    {rates.overheads.map((x) => <RateRow key={x.id} name={x.label} value={`${x.pct * 100}% of labour`} it={x} />)}
                    {rates.monthly_costs.map((x) => <RateRow key={x.id} name={x.label} value={`${x.pkr_per_month.toLocaleString("en-US")} / month`} it={x} />)}
                    {rates.one_time_costs.map((x) => <RateRow key={x.id} name={x.label} value={x.pkr.toLocaleString("en-US")} it={x} />)}
                    <RateRow name={rates.contingency.label} value={`${rates.contingency.pct * 100}%`} it={rates.contingency} />
                    <RateRow name={rates.tax.label} value={`${rates.tax.pct * 100}%`} it={rates.tax} />
                    <RateRow name={rates.maintenance.label} value={`${rates.maintenance.annual_pct_of_build * 100}% per year`} it={rates.maintenance} />
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          <p className="text-xs text-ink-muted border border-line bg-surface rounded-card px-4 py-3">{r.disclaimer} Rate table version {r.rates_meta.version}, last updated {r.rates_meta.last_updated}.</p>
        </>
      )}
    </div>
  );
}

function RateRow({ name, value, it }) {
  return (
    <tr className="border-b border-line align-top">
      <td className="py-1.5 text-ink pr-3">{name}</td>
      <td className="py-1.5 text-ink-muted pr-3 whitespace-nowrap">{value}</td>
      <td className="py-1.5 pr-3 whitespace-nowrap">
        <span className={it.verified ? "text-success" : "text-warning"}>{it.verified ? "Verified" : "Unverified"}</span>
        <span className="text-ink-muted/70"> · {it.last_updated}</span>
      </td>
      <td className="py-1.5 text-ink-muted/70 hidden sm:table-cell">{it.source}</td>
    </tr>
  );
}