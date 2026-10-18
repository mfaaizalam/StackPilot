import { Children, useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api from "../api/axios.js";
import MermaidBlock from "./MermaidBlock.jsx";

/* ───────── helpers ───────── */
const errText = (e, fallback = "Something went wrong. Please try again.") => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  return fallback;
};

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function Spinner() {
  return <span className="inline-block w-4 h-4 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" />;
}

// Job stages reported by the backend (sdd_service.run_sdd_job / build_design)
const STAGES = [
  { key: "collecting", label: "Reading the SRS and diagrams" },
  { key: "designing", label: "Designing components, API and database" },
  { key: "validating", label: "Checking traceability and layering" },
  { key: "repairing", label: "Fixing problems found", optional: true },
  { key: "saving", label: "Building the design document" },
];

/* Markdown elements styled with Tailwind; ```mermaid fences become drawn diagrams */
const md = {
  h1: (p) => <h1 className="text-3xl font-semibold tracking-tight text-neutral-900 mb-1" {...p} />,
  h2: (p) => <h2 className="text-xl font-semibold text-neutral-900 mt-10 mb-3 pb-2 border-b border-neutral-200" {...p} />,
  h3: (p) => <h3 className="text-base font-semibold text-neutral-900 mt-6 mb-2" {...p} />,
  h4: (p) => <h4 className="text-sm font-semibold text-neutral-800 mt-5 mb-1.5" {...p} />,
  p: (p) => <p className="text-sm text-neutral-700 leading-relaxed mb-3" {...p} />,
  ul: (p) => <ul className="list-disc pl-5 text-sm text-neutral-700 space-y-1 mb-3" {...p} />,
  ol: (p) => <ol className="list-decimal pl-5 text-sm text-neutral-700 space-y-1 mb-3" {...p} />,
  strong: (p) => <strong className="font-semibold text-neutral-900" {...p} />,
  code: (p) => <code className="text-[12px] bg-neutral-100 rounded px-1 py-0.5" {...p} />,
  table: (p) => <div className="overflow-x-auto mb-4"><table className="w-full text-sm border border-neutral-200 rounded-lg" {...p} /></div>,
  th: (p) => <th className="text-left font-semibold bg-neutral-50 border-b border-neutral-200 px-3 py-2 text-neutral-800" {...p} />,
  td: (p) => <td className="border-b border-neutral-100 px-3 py-2 text-neutral-700 align-top" {...p} />,
  pre: ({ children }) => {
    const child = Children.toArray(children)[0];
    const cls = child?.props?.className || "";
    if (/language-mermaid/.test(cls)) {
      return <MermaidBlock source={String(child.props.children).replace(/\n$/, "")} />;
    }
    return <pre className="text-xs bg-neutral-50 border border-neutral-200 rounded-lg p-3 overflow-x-auto mb-4 [&_code]:bg-transparent [&_code]:p-0">{children}</pre>;
  },
};

const LAYER_STYLE = {
  presentation: "bg-sky-50 text-sky-800 border-sky-100",
  api: "bg-violet-50 text-violet-800 border-violet-100",
  service: "bg-emerald-50 text-emerald-800 border-emerald-100",
  data: "bg-amber-50 text-amber-800 border-amber-100",
  integration: "bg-rose-50 text-rose-800 border-rose-100",
  infrastructure: "bg-neutral-100 text-neutral-700 border-neutral-200",
};
const METHOD_STYLE = {
  GET: "text-emerald-700", POST: "text-sky-700", PUT: "text-amber-700", PATCH: "text-amber-700", DELETE: "text-red-700",
};

function Section({ title, count, children }) {
  return (
    <section className="bg-white border border-neutral-200 rounded-2xl p-6">
      <h3 className="text-sm font-semibold text-neutral-900 mb-4">
        {title}{count != null && <span className="ml-2 text-xs font-normal text-neutral-400">{count}</span>}
      </h3>
      {children}
    </section>
  );
}

function Th({ children, className = "" }) {
  return <th className={`py-2 pr-3 font-medium text-left ${className}`}>{children}</th>;
}

function FrList({ ids }) {
  if (!ids?.length) return <span className="text-neutral-300">None</span>;
  return <span className="text-neutral-600">{ids.join(", ")}</span>;
}

/* ───────── "Design" tab: the structured model, read-only ───────── */
function DesignView({ design: d }) {
  return (
    <div className="space-y-6">
      <Section title="Architecture">
        <p className="text-sm font-medium text-neutral-900">{d.architecture_style}</p>
        <p className="text-sm text-neutral-600 leading-relaxed mt-1.5">{d.architecture_overview}</p>
        {d.technology_stack?.length > 0 && (
          <div className="overflow-x-auto mt-5">
            <table className="w-full text-sm">
              <thead><tr className="text-xs text-neutral-400 border-b border-neutral-200"><Th>Layer</Th><Th>Technology</Th><Th>Why</Th></tr></thead>
              <tbody>
                {d.technology_stack.map((t, i) => (
                  <tr key={i} className="border-b border-neutral-100 align-top">
                    <td className="py-2 pr-3 text-neutral-800 whitespace-nowrap">{t.layer}</td>
                    <td className="py-2 pr-3 font-medium text-neutral-900">{t.technology}</td>
                    <td className="py-2 text-neutral-600">{t.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Components" count={d.components?.length}>
        <div className="grid sm:grid-cols-2 gap-4">
          {d.components?.map((c) => (
            <div key={c.id} className="border border-neutral-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-neutral-900">{c.name}</p>
                <span className={`text-[10px] font-medium border rounded-full px-2 py-0.5 shrink-0 ${LAYER_STYLE[c.layer] || LAYER_STYLE.infrastructure}`}>{c.layer}</span>
              </div>
              <p className="text-xs text-neutral-400 mt-0.5">{c.id}{c.pattern !== "none" && ` · ${c.pattern}`}</p>
              <p className="text-sm text-neutral-600 mt-2 leading-relaxed">{c.responsibility}</p>
              <dl className="mt-3 space-y-1 text-xs">
                <div className="flex gap-2"><dt className="text-neutral-400 w-16 shrink-0">Implements</dt><dd><FrList ids={c.fr_ids} /></dd></div>
                <div className="flex gap-2"><dt className="text-neutral-400 w-16 shrink-0">Calls</dt><dd><FrList ids={c.depends_on} /></dd></div>
              </dl>
            </div>
          ))}
        </div>
      </Section>

      <Section title="API endpoints" count={d.endpoints?.length}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-neutral-400 border-b border-neutral-200"><Th>Method</Th><Th>Path</Th><Th>Summary</Th><Th className="hidden md:table-cell">Actor</Th><Th className="hidden md:table-cell">Implements</Th></tr></thead>
            <tbody>
              {d.endpoints?.map((e) => (
                <tr key={e.id} className="border-b border-neutral-100 align-top">
                  <td className={`py-2 pr-3 font-mono text-xs font-semibold ${METHOD_STYLE[e.method] || ""}`}>{e.method}</td>
                  <td className="py-2 pr-3 font-mono text-xs text-neutral-800 whitespace-nowrap">{e.path}{!e.auth_required && <span className="ml-1.5 font-sans text-[10px] text-neutral-400">public</span>}</td>
                  <td className="py-2 pr-3 text-neutral-600">{e.summary}</td>
                  <td className="py-2 pr-3 text-neutral-600 hidden md:table-cell">{e.actor}</td>
                  <td className="py-2 text-xs hidden md:table-cell"><FrList ids={e.fr_ids} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Database tables" count={d.tables?.length}>
        <div className="grid sm:grid-cols-2 gap-4">
          {d.tables?.map((t) => (
            <div key={t.table} className="border border-neutral-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-neutral-900 font-mono">{t.table}</p>
              <p className="text-xs text-neutral-400 mb-2">Stores {t.entity}</p>
              <ul className="space-y-0.5">{t.columns.map((c, i) => <li key={i} className="text-xs font-mono text-neutral-700">{c}</li>)}</ul>
              {t.indexes?.length > 0 && <p className="text-xs text-neutral-500 mt-2">Indexes: {t.indexes.join("; ")}</p>}
              {t.notes && <p className="text-xs text-neutral-500 mt-1">{t.notes}</p>}
            </div>
          ))}
        </div>
      </Section>

      <Section title="Quality tactics" count={d.quality_tactics?.length}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-neutral-400 border-b border-neutral-200"><Th>Requirement</Th><Th>Tactic</Th><Th>Realized by</Th></tr></thead>
            <tbody>
              {d.quality_tactics?.map((q) => (
                <tr key={q.nfr_id} className="border-b border-neutral-100 align-top">
                  <td className="py-2 pr-3 text-neutral-800 whitespace-nowrap">{q.nfr_id}</td>
                  <td className="py-2 pr-3 text-neutral-700">{q.tactic}</td>
                  <td className="py-2 text-xs"><FrList ids={q.realized_by} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Design decisions" count={d.decisions?.length}>
        <div className="space-y-4">
          {d.decisions?.map((x) => (
            <div key={x.id} className="border border-neutral-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-neutral-900">{x.title} <span className="text-xs font-normal text-neutral-400">{x.id}</span></p>
              <p className="text-sm text-neutral-700 mt-1.5">{x.decision}</p>
              <p className="text-sm text-neutral-500 mt-1.5"><span className="font-medium text-neutral-700">Why: </span>{x.rationale}</p>
              {x.alternatives?.length > 0 && <p className="text-xs text-neutral-500 mt-1.5"><span className="font-medium text-neutral-600">Rejected: </span>{x.alternatives.join("; ")}</p>}
            </div>
          ))}
        </div>
      </Section>

      {(d.error_handling?.length > 0 || d.design_risks?.length > 0) && (
        <div className="grid md:grid-cols-2 gap-6">
          {d.error_handling?.length > 0 && <Section title="Error handling"><ul className="list-disc pl-5 space-y-1.5 text-sm text-neutral-700">{d.error_handling.map((x, i) => <li key={i}>{x}</li>)}</ul></Section>}
          {d.design_risks?.length > 0 && <Section title="Design risks"><ul className="list-disc pl-5 space-y-1.5 text-sm text-neutral-700">{d.design_risks.map((x, i) => <li key={i}>{x}</li>)}</ul></Section>}
        </div>
      )}
    </div>
  );
}

/* ───────── "Checks" tab ───────── */
function IssuesView({ issues }) {
  if (!issues.length) {
    return (
      <div className="bg-white border border-neutral-200 rounded-2xl px-6 py-10 text-center">
        <p className="text-sm font-medium text-neutral-900">No problems found</p>
        <p className="text-sm text-neutral-500 mt-1">Every functional requirement is allocated and every quality requirement has a tactic.</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {issues.map((i, n) => (
        <div key={n} className={`rounded-xl border px-4 py-3 text-sm ${i.level === "error" ? "bg-red-50 border-red-100 text-red-800" : "bg-amber-50 border-amber-100 text-amber-800"}`}>
          <p className="text-[11px] font-medium opacity-70">{i.level === "error" ? "Problem" : "Warning"} · {i.code}</p>
          <p className="mt-0.5">{i.message}</p>
        </div>
      ))}
    </div>
  );
}

/* ───────── the panel ───────── */
export default function SddPanel({ boardId, srsId, version }) {
  const base = `/boards/${boardId}/sdd`;
  const [loading, setLoading] = useState(true);
  const [doc, setDoc] = useState(null);
  const [versions, setVersions] = useState([]);
  const [tab, setTab] = useState("document");
  const [stage, setStage] = useState(null);      // set while a job runs
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };

  const loadVersions = useCallback(async () => {
    try { const { data } = await api.get(`${base}/versions`); setVersions(data); } catch { /* list is optional */ }
  }, [base]);

  const loadDoc = useCallback(async (v) => {
    try {
      const { data } = await api.get(base, { params: v ? { version: v } : {} });
      setDoc(data);
    } catch (e) {
      if (e?.response?.status === 404) setDoc(null); else setError(errText(e));
    }
    setLoading(false);
  }, [base]);

  useEffect(() => { loadDoc(); loadVersions(); return stopPolling; }, [loadDoc, loadVersions]);

  const generate = async () => {
    setError(""); setStage("collecting");
    try {
      const { data } = await api.post(`${base}/generate`, { srs_id: srsId });
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const { data: st } = await api.get(`${base}/jobs/${data.job_id}`);
          if (st.stage) setStage(st.stage);
          if (st.status === "done") { stopPolling(); setStage(null); setTab("document"); await loadDoc(); loadVersions(); }
          if (st.status === "failed") { stopPolling(); setStage(null); setError(st.error || "Design generation failed."); }
        } catch (e) {
          if ([401, 404].includes(e?.response?.status)) { stopPolling(); setStage(null); setError(errText(e)); }
        }
      }, 2000);
    } catch (e) { setStage(null); setError(errText(e)); }
  };

  const exportFile = async (ext) => {
    try {
      const { data } = await api.get(`${base}/export.${ext}`, { params: { version: doc.version }, responseType: "blob" });
      download(data, `SDD_v${doc.version}.${ext}`);
    } catch (e) { setError(errText(e, "Download failed.")); }
  };

  if (loading) return <div className="h-40 bg-white border border-neutral-200 rounded-2xl animate-pulse" />;

  const running = stage !== null;
  const outdated = doc && (doc.srs_outdated || doc.srs_id !== srsId);
  const errors = doc?.issues?.filter((i) => i.level === "error").length || 0;
  const TABS = [["document", "Design document"], ["design", "Components and API"], ["checks", "Quality checks"]];
  const stageIdx = STAGES.findIndex((s) => s.key === stage);

  return (
    <div className="space-y-5">
      {error && <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">{error}</p>}

      {running && (
        <div className="bg-white border border-neutral-200 rounded-2xl px-5 py-4 print:hidden">
          <p className="text-sm font-medium text-neutral-900 mb-3">Designing your system…</p>
          <ul className="space-y-2">
            {STAGES.filter((s) => !s.optional || s.key === stage).map((s) => {
              const i = STAGES.findIndex((x) => x.key === s.key);
              const done = i < stageIdx, now = s.key === stage;
              return (
                <li key={s.key} className={`flex items-center gap-2 text-sm ${done ? "text-neutral-400" : now ? "text-neutral-900" : "text-neutral-300"}`}>
                  <span className="w-4 flex justify-center">{done ? "✓" : now ? <Spinner /> : "•"}</span>{s.label}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!doc && !running && (
        <div className="bg-white border border-neutral-200 rounded-2xl px-8 py-14 text-center">
          <h2 className="text-lg font-semibold text-neutral-900">Turn this SRS into a design document</h2>
          <p className="text-sm text-neutral-500 mt-2 max-w-md mx-auto">
            We design the architecture, components, API endpoints, database tables and design decisions from SRS version {version} and your UML diagrams, and check that every requirement is covered. Generate the diagrams first for the best result.
          </p>
          <button onClick={generate} className="mt-6 text-sm font-medium px-5 py-2.5 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 transition">Generate design document</button>
        </div>
      )}

      {doc && (
        <>
          {outdated && !running && (
            <div className="flex flex-wrap items-center justify-between gap-3 text-sm bg-amber-50 border border-amber-100 text-amber-800 rounded-xl px-4 py-3 print:hidden">
              <span>This design was made from SRS version {doc.srs_version}, but the current version is {version}.</span>
              <button onClick={generate} className="text-xs font-medium px-3 py-1.5 rounded-lg bg-amber-800 text-white hover:bg-amber-900 transition">Regenerate</button>
            </div>
          )}
          {doc.source === "fallback" && (
            <p className="text-sm text-neutral-700 bg-neutral-100 border border-neutral-200 rounded-xl px-4 py-3 print:hidden">
              The AI service was unavailable, so this design was derived directly from the requirements. Review endpoints and component allocation before relying on them.
            </p>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
            <div className="flex flex-wrap gap-2">
              {TABS.map(([k, label]) => (
                <button key={k} onClick={() => setTab(k)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition ${tab === k ? "bg-neutral-950 text-white border-neutral-950" : "bg-white text-neutral-700 border-neutral-200 hover:bg-neutral-100"}`}>
                  {label}
                  {k === "checks" && doc.issues?.length > 0 && <span className={`ml-1.5 ${errors ? "text-red-400" : "opacity-60"}`}>{doc.issues.length}</span>}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {versions.length > 1 && (
                <select value={doc.version} onChange={(e) => loadDoc(Number(e.target.value))} aria-label="Design version"
                  className="text-xs border border-neutral-200 rounded-lg px-2 py-1.5 bg-white">
                  {versions.map((v) => <option key={v.id} value={v.version}>Version {v.version}</option>)}
                </select>
              )}
              <button onClick={() => exportFile("md")} className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">.md</button>
              <button onClick={() => exportFile("docx")} className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">Word</button>
              <button onClick={() => { setTab("document"); setTimeout(() => window.print(), 100); }} className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">PDF / Print</button>
              <button onClick={generate} disabled={running} className="text-xs font-medium px-3 py-1.5 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 disabled:opacity-50 transition">New version</button>
            </div>
          </div>

          {tab === "document" && (
            <div className="bg-white border border-neutral-200 rounded-2xl px-8 py-8 print:border-0 print:p-0">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{doc.markdown}</ReactMarkdown>
            </div>
          )}
          {tab === "design" && <div className="print:hidden"><DesignView design={doc.design} /></div>}
          {tab === "checks" && <div className="print:hidden"><IssuesView issues={doc.issues || []} /></div>}
        </>
      )}
    </div>
  );
}