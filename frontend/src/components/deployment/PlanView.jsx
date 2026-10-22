import { useState } from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { md } from "./mdComponents.jsx";
import { useDeploymentActions } from "../../api/deployment.js";
import { errText, fmtDate, pkr } from "../../utils/ganttFormat.js";

const stamp = (iso) => (iso ? fmtDate(iso.slice(0, 10)) : "");

export default function PlanView({ boardId, plan, plans, onPick, onUpdate, canEdit, canManageFinance, boardName }) {
  const { addToCosting } = useDeploymentActions(boardId);
  const [months, setMonths] = useState(12);
  const [result, setResult] = useState(null); // { ok, text }
  const send = () => {
    if (!window.confirm(`Add the monthly hosting cost x ${months} months to Costing as estimated expenses? Hosting lines from earlier versions are replaced.`)) return;
    addToCosting.mutate({ planId: plan.id, months }, {
      onSuccess: (r) => setResult({ ok: true, r }),
      onError: (e) => setResult({ ok: false, text: errText(e) }),
    });
  };
  const copy = () => navigator.clipboard?.writeText(plan.document_md);
  const download = () => {
    const url = URL.createObjectURL(new Blob([plan.document_md], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(boardName || "project").replace(/[^\w-]+/g, "-").toLowerCase()}-deployment-v${plan.version}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const btn = "text-xs px-3 py-1.5 rounded-lg border border-line bg-surface hover:bg-surface-2 transition";
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <label className="flex items-center gap-2 text-xs text-ink-muted">Version
          <select value={plan.id} onChange={(e) => onPick(Number(e.target.value))} className="text-xs border border-line rounded-lg px-2 py-1.5 bg-surface text-ink">
            {plans.map((p) => <option key={p.id} value={p.id}>v{p.version} · {stamp(p.created_at)}</option>)}
          </select>
        </label>
        <div className="flex flex-wrap gap-2">
          <button onClick={copy} className={btn}>Copy Markdown</button>
          <button onClick={download} className={btn}>Download .md</button>
          <button onClick={() => window.print()} className={btn}>Print / PDF</button>
          {canEdit && <button onClick={onUpdate} className="text-xs font-medium px-3 py-1.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition">Update stack or services</button>}
        </div>
      </div>
      {canManageFinance && (
        <div className="bg-surface border border-line rounded-card px-4 py-3 flex flex-wrap items-center justify-between gap-3 print:hidden">
          <div>
            <p className="text-sm font-medium text-ink">Add this hosting cost to Costing</p>
            <p className="text-xs text-ink-muted">Creates one estimated expense per paid service in the Hosting and infrastructure category, so it counts toward the project budget.</p>
          </div>
          <div className="flex items-center gap-2">
            <select value={months} onChange={(e) => setMonths(Number(e.target.value))} aria-label="Months of hosting" className="text-xs border border-line rounded-lg px-2 py-1.5 bg-surface text-ink">
              {[3, 6, 12, 24, 36].map((m) => <option key={m} value={m}>{m} months</option>)}
            </select>
            <button onClick={send} disabled={addToCosting.isPending} className="text-xs font-medium px-3 py-1.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">
              {addToCosting.isPending ? "Adding…" : "Add to Costing"}
            </button>
          </div>
        </div>
      )}
      {result && (
        <p className={`text-sm rounded-card px-4 py-3 border print:hidden ${result.ok ? "text-success bg-success-soft border-success/20" : "text-danger bg-danger-soft border-danger/20"}`}>
          {result.ok
            ? <>Added {result.r.added} hosting line{result.r.added === 1 ? "" : "s"} ({pkr(result.r.estimated_total)} for {result.r.months} months){result.r.removed ? `, replaced ${result.r.removed} earlier` : ""}{result.r.kept ? `, kept ${result.r.kept} that already have actual spending` : ""}. <Link className="underline" to={`/boards/${boardId}/costing`}>Open Costing</Link></>
            : result.text}
        </p>
      )}
      <article className="bg-surface border border-line rounded-card p-6 sm:p-8">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{plan.document_md}</ReactMarkdown>
      </article>
    </div>
  );
}
