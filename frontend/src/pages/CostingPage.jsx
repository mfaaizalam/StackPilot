import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useGantt, useGanttActions } from "../api/gantt.js";
import { useLatestSrs } from "../api/queries.js";
import { errText } from "../utils/ganttFormat.js";
import CostPanel from "../components/CostPanel.jsx";
import AlertBanner from "../components/gantt/AlertBanner.jsx";
import SummaryCards from "../components/gantt/SummaryCards.jsx";
import FinancePanel from "../components/gantt/FinancePanel.jsx";
import BudgetTimeline from "../components/gantt/BudgetTimeline.jsx";
import PhaseTable from "../components/gantt/PhaseTable.jsx";
import ActivityCostTable from "../components/costing/ActivityCostTable.jsx";
import CategoryBreakdown from "../components/costing/CategoryBreakdown.jsx";
import ExpensePanel from "../components/costing/ExpensePanel.jsx";

function Section({ title, sub, children }) {
  return (
    <section className="space-y-3">
      <div><h2 className="text-sm font-semibold text-ink">{title}</h2>{sub && <p className="text-xs text-ink-muted mt-0.5">{sub}</p>}</div>
      {children}
    </section>
  );
}

// Issue #7: the Costing tab. Budget and expenses (live tracking) plus the SRS-based PKR estimate (the old page).
function BudgetTab({ boardId }) {
  const { data, isLoading, error } = useGantt(boardId);
  const actions = useGanttActions(boardId);
  if (isLoading) return <div className="h-48 bg-surface border border-line rounded-card animate-pulse" />;
  if (error) return <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-card px-4 py-3">{errText(error, "Could not load the costing data.")}</p>;
  const hasData = data.activities.length > 0 || data.expenses.length > 0 || data.summary.timeline.length > 0 || Number(data.summary.base_budget) > 0;
  return (
    <div className="space-y-8">
      <AlertBanner alerts={data.summary.alerts} hasData={hasData} />
      <SummaryCards summary={data.summary} project={data.project} />

      <Section title="Activity-wise costs" sub="Estimated vs actual cost of every activity, rolled into the project total.">
        <ActivityCostTable data={data} actions={actions} boardId={boardId} />
      </Section>
      <Section title="Cost breakdown by category" sub="Labour, hosting, tools and other expense categories.">
        <CategoryBreakdown categories={data.categories} />
      </Section>
      <Section title="Expenses" sub="Add expense lines to an activity or to the whole project. They feed the totals above.">
        <ExpensePanel data={data} actions={actions} />
      </Section>
      <Section title="Project finance" sub="Base budget and finance increments (planned, approved, disbursed).">
        <FinancePanel key={data.summary.base_budget} data={data} canManage={data.can_manage_finance} actions={actions} />
      </Section>
      <Section title="Cumulative budget" sub="Budget after each increment, against actual cost.">
        <div className="bg-surface border border-line rounded-card p-4"><BudgetTimeline summary={data.summary} project={data.project} today={data.today} /></div>
      </Section>
      {data.phases.length > 0 && <Section title="Cost by phase"><PhaseTable phases={data.phases} /></Section>}
      <p className="text-xs text-ink-muted">Dates, durations and the Gantt chart are on the <Link className="underline" to={`/boards/${boardId}/timeline`}>Timeline</Link> page.</p>
    </div>
  );
}

function EstimateTab({ boardId }) {
  const navigate = useNavigate();
  const { data: doc, isLoading, error } = useLatestSrs(boardId);
  if (isLoading) return <div className="h-40 bg-surface border border-line rounded-card animate-pulse" />;
  if (error?.response?.status === 404) {
    return (
      <div className="bg-surface border border-dashed border-ink-muted/40 rounded-card px-6 py-14 text-center">
        <p className="text-base font-medium text-ink">No SRS yet for this project</p>
        <p className="mt-1.5 text-sm text-ink-muted max-w-sm mx-auto">The PKR cost estimate is built from the SRS requirements. Generate the SRS first.</p>
        <button onClick={() => navigate(`/boards/${boardId}/srs`)} className="mt-5 text-sm font-medium px-4 py-2.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition">Go to SRS</button>
      </div>
    );
  }
  if (error) return <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-card px-4 py-3">{errText(error, "Could not load the SRS for this project.")}</p>;
  return <CostPanel key={doc.id} boardId={boardId} srsId={doc.id} version={doc.version} />;
}

const TABS = [["budget", "Budget and expenses"], ["estimate", "Cost estimate (from SRS)"]];

export default function CostingPage() {
  const { boardId } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "estimate" ? "estimate" : "budget";
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="border-b border-line bg-surface sticky top-0 z-30 print:hidden">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
          <h1 className="text-sm font-semibold">Costing</h1>
          <div className="flex rounded-lg border border-line overflow-hidden" role="tablist">
            {TABS.map(([k, label]) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setParams(k === "budget" ? {} : { tab: k })}
                className={`text-xs px-3 py-1.5 transition ${tab === k ? "bg-brand text-brand-fg" : "bg-surface text-ink-muted hover:bg-surface-2"}`}>{label}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {tab === "budget" ? <BudgetTab boardId={boardId} /> : <EstimateTab boardId={boardId} />}
      </div>
    </div>
  );
}
