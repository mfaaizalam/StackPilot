import { useState } from "react";
import { useDeploymentActions, useSuggest } from "../../api/deployment.js";
import { errText } from "../../utils/ganttFormat.js";

const inputCls = "w-full text-sm text-ink border border-line rounded-lg px-2.5 py-2 bg-surface focus:outline-none focus:ring-2 focus:ring-brand/20";
const usd = (n) => (n === 0 ? "Free" : `USD ${n.toLocaleString("en-US")}`);
const pkr = (n) => `PKR ${Math.round(n).toLocaleString("en-US")}`;

function Select({ label, value, onChange, items }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-medium text-ink mb-1">{label}</span>
      <select className={inputCls} value={value} onChange={(e) => onChange(e.target.value)}>
        {items.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
      </select>
    </label>
  );
}

// Step 1 asks for the stack, step 2 shows priced suggestions per layer and the user's final pick,
// then the server generates the document. Prices come from the maintained table, never from an AI guess.
export default function DeploymentWizard({ boardId, options, initial, canEdit, onDone, onCancel }) {
  const suggest = useSuggest(boardId);
  const { generate } = useDeploymentActions(boardId);
  const [step, setStep] = useState(1);
  const [stack, setStack] = useState(initial?.stack ?? { frontend: "react", backend: "fastapi", database: "postgresql", scale: "small", extras: ["ci_cd", "monitoring"] });
  const [layers, setLayers] = useState([]);
  const [selected, setSelected] = useState(initial?.selected ?? {});
  const [meta, setMeta] = useState({ domain: initial?.options?.domain ?? "", environments: initial?.options?.environments ?? ["production"], notes: initial?.options?.notes ?? "" });
  const [err, setErr] = useState("");

  const toggle = (arr, v) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const getSuggestions = () => {
    setErr("");
    suggest.mutate(stack, {
      onSuccess: (r) => {
        setLayers(r.layers);
        // keep an earlier choice if it is still offered, otherwise take the recommended service
        setSelected((prev) => Object.fromEntries(r.layers.map((l) => [l.category, l.options.some((o) => o.service_id === prev[l.category]) ? prev[l.category] : l.options[0]?.service_id]).filter(([, v]) => v)));
        setStep(2);
      },
      onError: (e) => setErr(errText(e)),
    });
  };

  const chosen = layers.map((l) => l.options.find((o) => o.service_id === selected[l.category])).filter(Boolean);
  const totalUsd = chosen.reduce((t, o) => t + o.monthly_usd, 0);
  const totalPkr = chosen.reduce((t, o) => t + o.monthly_pkr, 0);
  const unverified = chosen.some((o) => !o.verified);

  const make = () => {
    setErr("");
    generate.mutate({ stack, selected, domain: meta.domain.trim() || null, environments: meta.environments, notes: meta.notes.trim() || null },
      { onSuccess: onDone, onError: (e) => setErr(errText(e)) });
  };

  return (
    <div className="space-y-6">
      <ol className="flex items-center gap-2 text-xs" aria-label="Steps">
        {["Your tech stack", "Choose services", "Document"].map((t, i) => (
          <li key={t} className={`px-3 py-1 rounded-full border ${step === i + 1 ? "bg-brand text-brand-fg border-brand" : i + 1 < step ? "bg-surface-2 text-ink border-line" : "text-ink-muted border-line"}`}>{i + 1}. {t}</li>
        ))}
      </ol>

      {step === 1 && (
        <div className="bg-surface border border-line rounded-card p-5 space-y-5">
          <div>
            <h2 className="text-sm font-semibold text-ink">What does your project use?</h2>
            <p className="text-xs text-ink-muted mt-0.5">We suggest hosting services that fit these choices and show their monthly price.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Select label="Frontend" value={stack.frontend} items={options.stack.frontend} onChange={(v) => setStack({ ...stack, frontend: v })} />
            <Select label="Backend" value={stack.backend} items={options.stack.backend} onChange={(v) => setStack({ ...stack, backend: v })} />
            <Select label="Database" value={stack.database} items={options.stack.database} onChange={(v) => setStack({ ...stack, database: v })} />
            <Select label="Expected size" value={stack.scale} items={options.stack.scale.map((s) => ({ value: s.value, label: options.scales[s.value] }))} onChange={(v) => setStack({ ...stack, scale: v })} />
          </div>
          <fieldset>
            <legend className="text-[11px] font-medium text-ink mb-2">Optional components</legend>
            <div className="flex flex-wrap gap-2">
              {options.extras.map((x) => {
                const on = stack.extras.includes(x.value);
                return (
                  <label key={x.value} className={`text-xs border rounded-full px-3 py-1.5 cursor-pointer transition ${on ? "bg-brand text-brand-fg border-brand" : "bg-surface text-ink-muted border-line hover:bg-surface-2"}`}>
                    <input type="checkbox" className="sr-only" checked={on} onChange={() => setStack({ ...stack, extras: toggle(stack.extras, x.value) })} />{x.label}
                  </label>
                );
              })}
            </div>
          </fieldset>
          {err && <p className="text-xs text-danger">{err}</p>}
          <div className="flex justify-end gap-2">
            {onCancel && <button onClick={onCancel} className="text-sm px-3.5 py-2 rounded-lg border border-line bg-surface hover:bg-surface-2 transition">Cancel</button>}
            <button onClick={getSuggestions} disabled={suggest.isPending} className="text-sm font-medium px-4 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">
              {suggest.isPending ? "Finding services…" : "Suggest services"}
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-6">
          {layers.length === 0 && <p className="text-sm text-ink-muted bg-surface border border-dashed border-ink-muted/40 rounded-card px-4 py-8 text-center">Your stack has no hosted layers. Go back and pick at least one.</p>}
          {layers.map((l) => (
            <section key={l.category} className="space-y-2">
              <h3 className="text-sm font-semibold text-ink">{l.label}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3" role="radiogroup" aria-label={l.label}>
                {l.options.map((o) => {
                  const on = selected[l.category] === o.service_id;
                  return (
                    <label key={o.service_id} className={`block border rounded-card p-4 cursor-pointer transition ${on ? "border-brand bg-brand/5 ring-2 ring-brand/20" : "border-line bg-surface hover:bg-surface-2/60"}`}>
                      <input type="radio" className="sr-only" name={l.category} checked={on} onChange={() => setSelected({ ...selected, [l.category]: o.service_id })} />
                      <div className="flex items-start justify-between gap-3">
                        <div><p className="text-sm font-semibold text-ink">{o.name}</p><p className="text-xs text-ink-muted">{o.plan}</p></div>
                        <div className="text-right shrink-0"><p className="text-sm font-semibold text-ink">{usd(o.monthly_usd)}{o.monthly_usd > 0 && <span className="text-[10px] font-normal text-ink-muted"> /mo</span>}</p>
                          {o.monthly_usd > 0 && <p className="text-[11px] text-ink-muted">{pkr(o.monthly_pkr)}</p>}</div>
                      </div>
                      <p className="text-xs text-ink-muted mt-2">{o.why}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-2.5 text-[10px]">
                        {o.recommended && <span className="px-2 py-0.5 rounded-full bg-success-soft text-success">Recommended</span>}
                        {!o.verified && <span className="px-2 py-0.5 rounded-full bg-warning-soft text-warning">Price not verified</span>}
                        <a href={o.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-brand underline">Pricing page</a>
                      </div>
                    </label>
                  );
                })}
              </div>
            </section>
          ))}

          {layers.length > 0 && (
            <div className="bg-surface border border-line rounded-card p-5 space-y-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">Your selection</h3>
                <p className="text-sm text-ink">Monthly total: <b>{usd(totalUsd)}</b> <span className="text-ink-muted">({pkr(totalPkr)}, yearly about {pkr(totalPkr * 12)})</span></p>
              </div>
              {unverified && <p className="text-xs text-warning bg-warning-soft border border-warning/30 rounded-lg px-3 py-2">Some prices are approximate and not yet verified (rate 1 USD = PKR {options.currency.usd_to_pkr}). Check the vendor pricing pages before quoting a client.</p>}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="block"><span className="block text-[11px] font-medium text-ink mb-1">Domain (optional)</span>
                  <input className={inputCls} placeholder="example.com" maxLength={100} value={meta.domain} onChange={(e) => setMeta({ ...meta, domain: e.target.value })} /></label>
                <fieldset><legend className="text-[11px] font-medium text-ink mb-1">Environments</legend>
                  <div className="flex gap-2 flex-wrap">{options.environments.map((en) => (
                    <label key={en} className={`text-xs border rounded-full px-3 py-1.5 cursor-pointer capitalize ${meta.environments.includes(en) ? "bg-brand text-brand-fg border-brand" : "bg-surface text-ink-muted border-line"}`}>
                      <input type="checkbox" className="sr-only" checked={meta.environments.includes(en)} onChange={() => setMeta({ ...meta, environments: toggle(meta.environments, en) })} />{en}</label>))}</div></fieldset>
              </div>
              <label className="block"><span className="block text-[11px] font-medium text-ink mb-1">Notes to include (optional): regions, constraints, access, anything the team should know</span>
                <textarea rows={3} maxLength={4000} className={inputCls} value={meta.notes} onChange={(e) => setMeta({ ...meta, notes: e.target.value })} /></label>
              {!canEdit && <p className="text-xs text-ink-muted">You have view access only, so you cannot generate the document.</p>}
              {err && <p className="text-xs text-danger">{err}</p>}
              <div className="flex justify-between gap-2">
                <button onClick={() => setStep(1)} className="text-sm px-3.5 py-2 rounded-lg border border-line bg-surface hover:bg-surface-2 transition">Back</button>
                <button onClick={make} disabled={!canEdit || generate.isPending || meta.environments.length === 0}
                  className="text-sm font-medium px-4 py-2 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition disabled:opacity-50">{generate.isPending ? "Generating…" : "Generate deployment document"}</button>
              </div>
            </div>
          )}
          {layers.length === 0 && <button onClick={() => setStep(1)} className="text-sm px-3.5 py-2 rounded-lg border border-line bg-surface hover:bg-surface-2 transition">Back</button>}
        </div>
      )}
    </div>
  );
}
