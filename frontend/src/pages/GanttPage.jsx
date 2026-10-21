import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useGantt, useGanttActions } from "../api/gantt.js";
import { errText } from "../utils/ganttFormat.js";
import AlertBanner from "../components/gantt/AlertBanner.jsx";
import SummaryCards from "../components/gantt/SummaryCards.jsx";
import GanttChart from "../components/gantt/GanttChart.jsx";
import ActivityTable from "../components/gantt/ActivityTable.jsx";
import FinancePanel from "../components/gantt/FinancePanel.jsx";
import BudgetTimeline from "../components/gantt/BudgetTimeline.jsx";
import PhaseTable from "../components/gantt/PhaseTable.jsx";

function Section({ title, sub, children }) {
  return (
    <section className="space-y-3">
      <div><h2 className="text-sm font-semibold text-ink">{title}</h2>{sub && <p className="text-xs text-ink-muted mt-0.5">{sub}</p>}</div>
      {children}
    </section>
  );
}

export default function GanttPage() {
  const { boardId } = useParams();
  const { data, isLoading, error } = useGantt(boardId);
  const actions = useGanttActions(boardId);
  const [msg, setMsg] = useState(null); // { ok: bool, text }

  const seed = (mode) =>
    actions.seed.mutate(mode, {
      onSuccess: (r) => setMsg({ ok: true, text: r.added ? `Added ${r.added} activities from your Kanban board${r.used_cost_estimate ? " using your latest cost estimate." : ". Generate a cost estimate to fill in costs."}` : "Every task already has an activity." }),
      onError: (e) => setMsg({ ok: false, text: errText(e) }),
    });

  const has = data?.activities?.length > 0;
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="border-b border-line bg-surface sticky top-0 z-30 print:hidden">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
          <h1 className="text-sm font-semibold">Timeline and finance</h1>
          <div className="flex items-center gap-2">
            <Link to={`/boards/${boardId}/costing`} className="hidden sm:inline text-xs text-ink-muted hover:text-ink">Cost estimate</Link>
            <Link to={`/boards/${boardId}/kanban`} className="hidden sm:inline text-xs text-ink-muted hover:text-ink mr-2">Kanban</Link>
            {data?.can_manage_finance && (
              <button onClick={() => seed(has ? "sync" : "create")} disabled={actions.seed.isPending}
                className="text-sm font-medium px-3.5 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">
                {actions.seed.isPending ? "Generating…" : has ? "Add missing from board" : "Generate from board"}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {isLoading && <div className="h-48 bg-surface border border-line rounded-card animate-pulse" />}
        {error && (
          <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-card px-4 py-3">
            {error?.response?.status === 404 ? "Board not found." : errText(error, "Could not load the timeline. Please try again.")}
          </p>
        )}
        {msg && (
          <p className={`text-sm rounded-card px-4 py-3 border ${msg.ok ? "text-success bg-success-soft border-success/20" : "text-danger bg-danger-soft border-danger/20"}`}>
            {msg.text} {!msg.ok && /no tasks/i.test(msg.text) && <Link className="underline" to={`/boards/${boardId}/srs`}>Go to SRS</Link>}
          </p>
        )}

        {data && (
          <>
            <AlertBanner alerts={data.summary.alerts} hasData={has || data.summary.timeline.length > 0 || Number(data.summary.base_budget) > 0} />
            <SummaryCards summary={data.summary} project={data.project} />

            <Section title="Gantt chart" sub="Bar length is duration, the dark part is progress. Hover a bar for details.">
              <GanttChart activities={data.activities} today={data.today} />
            </Section>

            <Section title="Activities" sub="Time allocation, estimated vs actual cost, and progress against budget and hours.">
              <ActivityTable activities={data.activities} canEdit={data.can_edit} actions={actions} />
            </Section>

            <Section title="Project finance" sub="Base budget plus planned, approved and disbursed increments.">
              <FinancePanel key={data.summary.base_budget} data={data} canManage={data.can_manage_finance} actions={actions} />
            </Section>

            <Section title="Cumulative budget" sub="How the project budget grows after each increment, against actual cost.">
              <div className="bg-surface border border-line rounded-card p-4">
                <BudgetTimeline summary={data.summary} project={data.project} today={data.today} />
              </div>
            </Section>

            {data.phases.length > 0 && (
              <Section title="Cost by phase" sub="Spend against the funding tagged to each phase.">
                <PhaseTable phases={data.phases} />
              </Section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
