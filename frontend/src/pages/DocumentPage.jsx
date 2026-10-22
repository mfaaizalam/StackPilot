import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useDeploymentOptions, usePlan, usePlans } from "../api/deployment.js";
import { useBoards } from "../api/queries.js";
import { errText } from "../utils/ganttFormat.js";
import DeploymentWizard from "../components/deployment/DeploymentWizard.jsx";
import PlanView from "../components/deployment/PlanView.jsx";
import SupportingDocs from "../components/deployment/SupportingDocs.jsx";

const TABS = [["deployment", "Deployment document"], ["files", "Plans and notes"]];

// Issue #7: the Document tab. Wizard (stack -> priced suggestions -> choice -> generated document) and a place for supporting documents.
function DeploymentTab({ boardId, boardName }) {
  const { data: options, error: optErr } = useDeploymentOptions(boardId);
  const { data: plans, isLoading, error: plansErr } = usePlans(boardId);
  const [mode, setMode] = useState("view");
  const [pickedId, setPickedId] = useState(null);
  const currentId = pickedId ?? plans?.[0]?.id;
  const { data: plan } = usePlan(boardId, currentId);

  const err = optErr || plansErr;
  if (err) return <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-card px-4 py-3">{errText(err, "Could not load the deployment document.")}</p>;
  if (isLoading || !options) return <div className="h-48 bg-surface border border-line rounded-card animate-pulse" />;

  const hasPlans = plans.length > 0;
  if (mode === "wizard" || !hasPlans) {
    return (
      <div className="space-y-4">
        {!hasPlans && <p className="text-sm text-ink-muted">No deployment document yet. Tell us your tech stack and we will suggest services, show prices and build the document.</p>}
        <DeploymentWizard key={plan?.id ?? "new"} boardId={boardId} options={options} canEdit={options.can_edit}
          initial={mode === "wizard" ? plan : undefined}
          onCancel={hasPlans ? () => setMode("view") : undefined}
          onDone={(p) => { setPickedId(p.id); setMode("view"); }} />
      </div>
    );
  }
  if (!plan) return <div className="h-48 bg-surface border border-line rounded-card animate-pulse" />;
  return <PlanView boardId={boardId} plan={plan} plans={plans} boardName={boardName} canEdit={options.can_edit} canManageFinance={options.can_manage_finance} onPick={setPickedId} onUpdate={() => setMode("wizard")} />;
}

function FilesTab({ boardId }) {
  const { data: options } = useDeploymentOptions(boardId);
  return <SupportingDocs boardId={boardId} canEdit={!!options?.can_edit} />;
}

export default function DocumentPage() {
  const { boardId } = useParams();
  const [params, setParams] = useSearchParams();
  const { data: boards } = useBoards();
  const boardName = boards?.find((b) => String(b.id) === String(boardId))?.name;
  const tab = params.get("tab") === "files" ? "files" : "deployment";
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <div className="border-b border-line bg-surface sticky top-0 z-30 print:hidden">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
          <h1 className="text-sm font-semibold">Document</h1>
          <div className="flex rounded-lg border border-line overflow-hidden" role="tablist">
            {TABS.map(([k, label]) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setParams(k === "deployment" ? {} : { tab: k })}
                className={`text-xs px-3 py-1.5 transition ${tab === k ? "bg-brand text-brand-fg" : "bg-surface text-ink-muted hover:bg-surface-2"}`}>{label}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {tab === "deployment" ? <DeploymentTab boardId={boardId} boardName={boardName} /> : <FilesTab boardId={boardId} />}
      </div>
    </div>
  );
}
