import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api from "../api/axios.js";
import DiagramsPanel from "../components/DiagramsPanel.jsx";
import ComingSoon from "../components/ComingSoon.jsx";

/* ───────────────────────── helpers s───────────────────────── */
const errText = (e, fallback = "Something went wrong. Please try again.") => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg; // FastAPI validation error
  return fallback;
};

const EXAMPLES = [
  "A hospital management system where patients book appointments, doctors record diagnoses and prescriptions, and pharmacists dispense medicine.",
  "An online store for a clothing brand with product catalogue, cart, Cash-on-Delivery and card payments, order tracking and an admin dashboard.",
  "A university portal where students register for courses, teachers upload marks and attendance, and admins publish timetables and results.",
];

const STAGES = [
  { key: "requirements", label: "Writing requirements" },
  { key: "validating", label: "Checking logic and traceability" },
  { key: "repairing", label: "Fixing problems found", optional: true },
  { key: "saving", label: "Building the SRS document" },
];

function Spinner() {
  return <span className="inline-block w-4 h-4 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" />;
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

/* Markdown elements styled with Tailwind (no typography plugin needed) */
const md = {
  h1: (p) => <h1 className="text-3xl font-semibold tracking-tight text-neutral-900 mb-1" {...p} />,
  h2: (p) => <h2 className="text-xl font-semibold text-neutral-900 mt-10 mb-3 pb-2 border-b border-neutral-200" {...p} />,
  h3: (p) => <h3 className="text-base font-semibold text-neutral-900 mt-6 mb-2" {...p} />,
  h4: (p) => <h4 className="text-sm font-semibold text-neutral-800 mt-5 mb-1.5" {...p} />,
  p: (p) => <p className="text-sm text-neutral-700 leading-relaxed mb-3" {...p} />,
  ul: (p) => <ul className="list-disc pl-5 text-sm text-neutral-700 space-y-1 mb-3" {...p} />,
  ol: (p) => <ol className="list-decimal pl-5 text-sm text-neutral-700 space-y-1 mb-3" {...p} />,
  strong: (p) => <strong className="font-semibold text-neutral-900" {...p} />,
  table: (p) => <div className="overflow-x-auto mb-4"><table className="w-full text-sm border border-neutral-200 rounded-lg" {...p} /></div>,
  th: (p) => <th className="text-left font-semibold bg-neutral-50 border-b border-neutral-200 px-3 py-2 text-neutral-800" {...p} />,
  td: (p) => <td className="border-b border-neutral-100 px-3 py-2 text-neutral-700 align-top" {...p} />,
};

const PRIORITY_STYLE = {
  must: "bg-red-50 text-red-700 border-red-100",
  should: "bg-amber-50 text-amber-700 border-amber-100",
  could: "bg-neutral-100 text-neutral-600 border-neutral-200",
};

/* ───────────────────────── steps ───────────────────────── */
function DescribeStep({ value, onChange, onNext, onSkip, busy, error }) {
  const ok = value.trim().length >= 20;
  return (
    <div className="max-w-2xl mx-auto">
      <p className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1.5">Step 1 of 3</p>
      <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">Describe your project</h1>
      <p className="text-sm text-neutral-500 mt-2 mb-5">
        A few sentences are enough: who uses it, and what it should do. We'll ask a few follow-up questions next.
      </p>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={7}
        maxLength={4000}
        placeholder="e.g. A hospital management system where patients book appointments…"
        className="w-full text-sm border border-neutral-200 rounded-xl px-4 py-3 bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-400 resize-y"
      />
      <div className="flex justify-between text-xs text-neutral-400 mt-1.5">
        <span>{ok ? "" : "Write at least 20 characters."}</span><span>{value.length}/4000</span>
      </div>

      <p className="text-xs font-medium text-neutral-500 mt-5 mb-2">Try an example</p>
      <div className="flex flex-col gap-2">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => onChange(ex)}
            className="text-left text-xs text-neutral-600 border border-neutral-200 bg-white rounded-lg px-3 py-2 hover:bg-neutral-100 transition">
            {ex}
          </button>
        ))}
      </div>

      {error && <p className="mt-5 text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">{error}</p>}

      <div className="flex items-center gap-3 mt-6">
        <button onClick={onNext} disabled={!ok || busy}
          className="inline-flex items-center gap-2 text-sm font-medium px-5 py-2.5 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 transition disabled:opacity-40">
          {busy && <Spinner />} {busy ? "Thinking of questions…" : "Continue"}
        </button>
        <button onClick={onSkip} disabled={!ok || busy}
          className="text-sm text-neutral-500 hover:text-neutral-900 underline underline-offset-2 disabled:opacity-40">
          Skip questions and generate
        </button>
      </div>
    </div>
  );
}

function QuestionsStep({ questions, answers, setAnswers, onBack, onGenerate, busy, error }) {
  const set = (id, v) => setAnswers((a) => ({ ...a, [id]: v }));
  return (
    <div className="max-w-2xl mx-auto">
      <p className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1.5">Step 2 of 3</p>
      <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">A few quick questions</h1>
      <p className="text-sm text-neutral-500 mt-2 mb-6">Tap an option or type your own. Anything you skip becomes a documented assumption.</p>

      <div className="space-y-5">
        {questions.map((q, i) => {
          const val = answers[q.id] || "";
          const custom = val && !q.options.includes(val);
          return (
            <div key={q.id} className="bg-white border border-neutral-200 rounded-2xl p-5">
              <p className="text-sm font-medium text-neutral-900 mb-3">{i + 1}. {q.question}</p>
              <div className="flex flex-wrap gap-2 mb-3">
                {q.options.map((o) => (
                  <button key={o} onClick={() => set(q.id, val === o ? "" : o)}
                    className={`text-xs px-3 py-1.5 rounded-full border transition ${val === o ? "bg-neutral-950 text-white border-neutral-950" : "bg-white text-neutral-700 border-neutral-200 hover:bg-neutral-100"}`}>
                    {o}
                  </button>
                ))}
              </div>
              <input
                value={custom ? val : ""}
                onChange={(e) => set(q.id, e.target.value)}
                maxLength={500}
                placeholder="…or type your own answer"
                className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-neutral-900/10"
              />
            </div>
          );
        })}
      </div>

      {error && <p className="mt-5 text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">{error}</p>}
      <div className="flex items-center gap-3 mt-6">
        <button onClick={onGenerate} disabled={busy}
          className="inline-flex items-center gap-2 text-sm font-medium px-5 py-2.5 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 transition disabled:opacity-40">
          {busy && <Spinner />} Generate SRS
        </button>
        <button onClick={onBack} className="text-sm text-neutral-500 hover:text-neutral-900">Back</button>
      </div>
    </div>
  );
}

function ProgressStep({ stage, error, onRetry }) {
  const idx = Math.max(0, STAGES.findIndex((s) => s.key === stage));
  const visible = STAGES.filter((s) => !s.optional || s.key === stage);
  return (
    <div className="max-w-md mx-auto text-center py-10">
      <p className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1.5">Step 3 of 3</p>
      <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 mb-1">
        {error ? "Generation failed" : "Building your SRS"}
      </h1>
      <p className="text-sm text-neutral-500 mb-8">{error ? "" : "This usually takes under two minutes."}</p>

      {error ? (
        <>
          <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-4">{error}</p>
          <button onClick={onRetry} className="text-sm font-medium px-4 py-2 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 transition">Back</button>
        </>
      ) : (
        <ul className="text-left space-y-3 inline-block">
          {visible.map((s) => {
            const i = STAGES.indexOf(s);
            const done = i < idx, active = i === idx;
            return (
              <li key={s.key} className="flex items-center gap-3 text-sm">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] ${done ? "bg-emerald-500 text-white" : active ? "bg-neutral-950 text-white" : "bg-neutral-200 text-neutral-400"}`}>
                  {done ? "✓" : active ? <span className="w-2 h-2 bg-white rounded-full animate-pulse" /> : ""}
                </span>
                <span className={done ? "text-neutral-400" : active ? "text-neutral-900 font-medium" : "text-neutral-400"}>{s.label}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/* ───────────────────────── result tabs ───────────────────────── */
function RequirementsTab({ req, onSave, saving }) {
  const [draft, setDraft] = useState(req);
  const [dirty, setDirty] = useState(false);
  useEffect(() => { setDraft(req); setDirty(false); }, [req]);

  const editFR = (id, patch) => {
    setDraft((d) => ({ ...d, functional_requirements: d.functional_requirements.map((f) => (f.id === id ? { ...f, ...patch } : f)) }));
    setDirty(true);
  };
  const editNFR = (id, patch) => {
    setDraft((d) => ({ ...d, non_functional_requirements: d.non_functional_requirements.map((f) => (f.id === id ? { ...f, ...patch } : f)) }));
    setDirty(true);
  };

  return (
    <div className="space-y-8 print:hidden">
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-500">Edit a requirement, then save. Saving creates a new version and re-runs the checks.</p>
        <button onClick={() => onSave(draft)} disabled={!dirty || saving}
          className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 transition disabled:opacity-40">
          {saving && <Spinner />} Save as new version
        </button>
      </div>

      <section>
        <h3 className="text-sm font-semibold text-neutral-900 mb-3">Functional requirements ({draft.functional_requirements.length})</h3>
        <div className="space-y-3">
          {draft.functional_requirements.map((f) => (
            <div key={f.id} className="bg-white border border-neutral-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-mono font-semibold text-neutral-500">{f.id}</span>
                <input value={f.title} onChange={(e) => editFR(f.id, { title: e.target.value })}
                  className="flex-1 text-sm font-medium text-neutral-900 border-0 border-b border-transparent hover:border-neutral-200 focus:border-neutral-400 focus:outline-none bg-transparent px-1" />
                <select value={f.priority} onChange={(e) => editFR(f.id, { priority: e.target.value })}
                  className={`text-xs border rounded-full px-2 py-1 ${PRIORITY_STYLE[f.priority]}`}>
                  <option value="must">must</option><option value="should">should</option><option value="could">could</option>
                </select>
              </div>
              <textarea value={f.statement} onChange={(e) => editFR(f.id, { statement: e.target.value })} rows={2}
                className="w-full text-sm text-neutral-700 border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 resize-y" />
              <p className="text-xs text-neutral-400 mt-1.5">Actor: {f.actor}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-neutral-900 mb-3">Non-functional requirements ({draft.non_functional_requirements.length})</h3>
        <div className="space-y-3">
          {draft.non_functional_requirements.map((n) => (
            <div key={n.id} className="bg-white border border-neutral-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2 text-xs">
                <span className="font-mono font-semibold text-neutral-500">{n.id}</span>
                <span className="px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600">{n.category}</span>
              </div>
              <textarea value={n.statement} onChange={(e) => editNFR(n.id, { statement: e.target.value })} rows={2}
                className="w-full text-sm text-neutral-700 border border-neutral-200 rounded-lg px-3 py-2 mb-2 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 resize-y" />
              <input value={n.metric} onChange={(e) => editNFR(n.id, { metric: e.target.value })}
                placeholder="Measurable target, e.g. 95% under 2 seconds"
                className="w-full text-sm text-neutral-700 border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-neutral-900/10" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function QualityTab({ issues }) {
  const errors = issues.filter((i) => i.level === "error");
  const warnings = issues.filter((i) => i.level === "warning");
  if (!issues.length)
    return <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-3 print:hidden">All automatic checks passed: IDs, actors, references and traceability.</p>;
  return (
    <div className="space-y-3 print:hidden">
      {[...errors, ...warnings].map((i, k) => (
        <div key={k} className={`text-sm rounded-xl px-4 py-3 border ${i.level === "error" ? "bg-red-50 border-red-100 text-red-700" : "bg-amber-50 border-amber-100 text-amber-800"}`}>
          <span className="font-semibold uppercase text-xs mr-2">{i.level}</span>{i.message}
        </div>
      ))}
    </div>
  );
}

/* ───────────────────────── generate board dialog ───────────────────────── */
function BoardDialog({ state, busy, onClose, onChoose, onOpenBoard }) {
  const [confirmReplace, setConfirmReplace] = useState(false);
  useEffect(() => { setConfirmReplace(false); }, [state]); // a reopened dialog never starts in the 'are you sure' step
  if (!state) return null;
  const card = "relative w-full max-w-md bg-white rounded-2xl border border-neutral-200 shadow-xl p-6";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 print:hidden">
      <div className="absolute inset-0 bg-neutral-950/40 backdrop-blur-sm" onClick={busy ? undefined : onClose} />

      {state.kind === "exists" && (
        <div className={card}>
          <h2 className="text-base font-semibold tracking-tight text-neutral-900">This board already has content</h2>
          <p className="text-sm text-neutral-600 mt-2">Nothing has been changed. Choose how to continue:</p>
          <div className="mt-4 space-y-2">
            <button disabled={busy} onClick={() => onChoose("sync")}
              className="w-full text-left rounded-xl border border-neutral-200 px-4 py-3 hover:bg-neutral-50 disabled:opacity-50 transition">
              <span className="block text-sm font-medium text-neutral-900">Add missing requirements</span>
              <span className="block text-xs text-neutral-500 mt-0.5">Keeps every existing task exactly as it is and only adds tasks for requirements that have none yet.</span>
            </button>
            {!confirmReplace ? (
              <button disabled={busy} onClick={() => setConfirmReplace(true)}
                className="w-full text-left rounded-xl border border-red-100 px-4 py-3 hover:bg-red-50 disabled:opacity-50 transition">
                <span className="block text-sm font-medium text-red-700">Replace the whole board</span>
                <span className="block text-xs text-neutral-500 mt-0.5">Deletes all columns and tasks on this board, then builds it again from this SRS.</span>
              </button>
            ) : (
              <button disabled={busy} onClick={() => onChoose("replace")}
                className="w-full rounded-xl bg-red-600 text-white px-4 py-3 text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition">
                {busy ? "Rebuilding…" : "Yes, delete everything and rebuild"}
              </button>
            )}
          </div>
          <button disabled={busy} onClick={onClose} className="mt-4 w-full py-2.5 rounded-lg border border-neutral-200 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 transition">Cancel</button>
        </div>
      )}

      {state.kind === "done" && (
        <div className={card}>
          <h2 className="text-base font-semibold tracking-tight text-neutral-900">
            {state.result.tasks_created > 0 ? "Board ready" : "Board is already up to date"}
          </h2>
          <p className="text-sm text-neutral-600 mt-2">
            {state.result.tasks_created} task{state.result.tasks_created === 1 ? "" : "s"} created from SRS v{state.result.version}
            {state.result.tasks_created > 0 && <> · {state.result.points_total} story points</>}
            {state.result.tasks_skipped > 0 && <> · {state.result.tasks_skipped} already on the board</>}.
          </p>
          {state.result.warnings?.length > 0 && (
            <div className="mt-3 rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 max-h-40 overflow-y-auto">
              <p className="text-xs font-semibold text-amber-900 mb-1">Worth a look</p>
              <ul className="list-disc pl-4 space-y-0.5 text-xs text-amber-900">
                {state.result.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
          <div className="mt-5 flex gap-2">
            <button onClick={onClose} className="flex-1 py-2.5 rounded-lg border border-neutral-200 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition">Stay here</button>
            <button onClick={onOpenBoard} className="flex-1 py-2.5 rounded-lg bg-neutral-950 text-white text-sm font-medium hover:bg-neutral-800 transition">Open board</button>
          </div>
        </div>
      )}

      {state.kind === "error" && (
        <div className={card}>
          <h2 className="text-base font-semibold tracking-tight text-neutral-900">Could not build the board</h2>
          <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mt-3">{state.message}</p>
          <button onClick={onClose} className="mt-4 w-full py-2.5 rounded-lg bg-neutral-950 text-white text-sm font-medium hover:bg-neutral-800 transition">Close</button>
        </div>
      )}
    </div>
  );
}

/* ───────────────────────── page ───────────────────────── */
// Diagrams and Costing also exist as standalone pages (DiagramsPage / CostingPage).
// The tabs here show the same panels for whichever SRS version is selected.
export default function SrsStudio() {
  const { boardId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // If this board's SRS was opened recently, start from the cached copy so the
  // page appears instantly instead of showing a skeleton and re-downloading it.
  const cachedLatest = queryClient.getQueryData(["srs", boardId, "latest"]);

  const [step, setStep] = useState(cachedLatest ? "result" : "loading"); // loading|describe|questions|progress|result|demo
  const [demoData, setDemoData] = useState(null);
  const [demoNotice, setDemoNotice] = useState("");
  const jobStartedAt = useRef(0);
  const [description, setDescription] = useState("");
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [stage, setStage] = useState("requirements");
  const [jobError, setJobError] = useState("");
  const [doc, setDoc] = useState(cachedLatest ?? null);
  const [versions, setVersions] = useState(queryClient.getQueryData(["srs-versions", boardId]) ?? []);
  const [tab, setTab] = useState("srs");
  // Heavy tabs (Diagrams, Cost) are mounted the first time they are opened and then
  // kept mounted (just hidden), so opening the page does not fetch them and switching
  // tabs back and forth does not refetch them.
  const [visited, setVisited] = useState({});
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [boardDialog, setBoardDialog] = useState(null); // null | {kind: exists|done|error, ...}
  const [boardBusy, setBoardBusy] = useState(false);
  const pollRef = useRef(null);

  const flash = (m) => { setToast(m); setTimeout(() => setToast(""), 2500); };
  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };

  const openTab = (k) => {
    setTab(k);
    setVisited((v) => (v[k] ? v : { ...v, [k]: true }));
  };

  // Cached for 60 s. Any write request in the app (axios interceptor) marks these stale.
  const loadVersions = useCallback(async (force = false) => {
    try {
      const data = await queryClient.fetchQuery({
        queryKey: ["srs-versions", boardId],
        staleTime: force ? 0 : 60_000,
        queryFn: () => api.get(`/boards/${boardId}/srs/versions`).then((r) => r.data),
      });
      setVersions(data);
    } catch { /* ignore */ }
  }, [boardId, queryClient]);

  const loadDoc = useCallback(async (version, force = false) => {
    const data = await queryClient.fetchQuery({
      queryKey: ["srs", boardId, version ?? "latest"],
      staleTime: force ? 0 : 60_000,
      queryFn: () =>
        api.get(`/boards/${boardId}/srs/`, { params: version ? { version } : {} }).then((r) => r.data),
    });
    setDoc(data); setStep("result"); setTab("srs"); setVisited({});
    loadVersions(force);
  }, [boardId, loadVersions, queryClient]);

  useEffect(() => {
    (async () => {
      try { await loadDoc(); return; } catch (e) { if (e?.response?.status !== 404) setError(errText(e)); }
      try {
        const b = await queryClient.fetchQuery({
          queryKey: ["board", boardId],
          staleTime: 5 * 60_000,
          queryFn: () => api.get(`/boards/${boardId}`).then((r) => r.data),
        });
        if (b?.description) setDescription(b.description);
      } catch { /* ignore */ }
      setStep("describe");
    })();
    return stopPolling;
  }, [boardId, loadDoc, queryClient]);

  // Demo fixtures are static, so they are cached for the whole session.
  const loadDemo = async (name = "hospital", reason = "") => {
    try {
      const data = await queryClient.fetchQuery({
        queryKey: ["demo", name],
        staleTime: Infinity,
        queryFn: () => api.get(`/demo/${name}`).then((r) => r.data),
      });
      setDemoData(data);
      setDemoNotice(reason || "Offline exhibition example loaded. This is prebuilt sample data, not a live AI result.");
      setStep("demo");
      setError("");
      setJobError("");
    } catch {
      setError("Could not load the offline example. Please check that the backend includes Phase 6 demo fixtures.");
    }
  };

  const fetchQuestions = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await api.post(`/boards/${boardId}/srs/questions`, { description });
      setQuestions(data.questions); setAnswers({}); setStep("questions");
    } catch (e) {
      if (!e?.response || e.response.status >= 500 || e.response.status === 429) {
        await loadDemo("hospital", `Live question generation failed: ${errText(e)} Showing the offline exhibition example instead.`);
      } else { setError(errText(e)); }
    }
    setBusy(false);
  };

  const startJob = async (useAnswers) => {
    setBusy(true); setError(""); setJobError(""); setStage("requirements");
    jobStartedAt.current = Date.now();
    const payload = {
      description,
      answers: useAnswers ? questions.filter((q) => answers[q.id]).map((q) => ({ question: q.question, answer: answers[q.id] })) : [],
    };
    try {
      const { data } = await api.post(`/boards/${boardId}/srs/generate`, payload);
      setStep("progress"); setBusy(false);
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          if (Date.now() - jobStartedAt.current > 60000) { stopPolling(); await loadDemo("hospital", "Live generation took longer than 60 seconds. Switched to the offline exhibition example."); return; }
          const { data: st } = await api.get(`/boards/${boardId}/srs/jobs/${data.job_id}`);
          setStage(st.stage);
          if (st.status === "done") { stopPolling(); await loadDoc(undefined, true); } // force: a new version now exists
          if (st.status === "failed") { stopPolling(); await loadDemo("hospital", `Live generation failed: ${st.error || "Generation failed."} Showing the offline exhibition example instead.`); }
        } catch (e) {
          if ([401, 404].includes(e?.response?.status)) { stopPolling(); setJobError(errText(e)); }
          // other errors (network blips): keep polling
        }
      }, 2000);
    } catch (e) {
      if (!e?.response || e.response.status >= 500 || e.response.status === 429) {
        await loadDemo("hospital", `Live generation could not start: ${errText(e)} Showing the offline exhibition example instead.`);
      } else { setError(errText(e)); }
      setBusy(false);
    }
  };

  const saveEdits = async (req) => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/boards/${boardId}/srs/requirements`, req);
      setDoc(data);
      // keep the cache in step with what the server just saved
      queryClient.setQueryData(["srs", boardId, "latest"], data);
      queryClient.setQueryData(["srs", boardId, data.version], data);
      loadVersions(true);
      flash(`Saved as version ${data.version}`);
    } catch (e) { flash(errText(e, "Could not save changes.")); }
    setSaving(false);
  };

  // SRS -> Kanban. Deterministic on the server (no AI), so this returns in well under a second.
  const buildBoard = async (mode = "create") => {
    setBoardBusy(true);
    try {
      const { data } = await api.post(`/boards/${boardId}/srs/generate-board`, { srs_id: doc.id, mode });
      setBoardDialog({ kind: "done", result: data });
    } catch (e) {
      if (e?.response?.status === 409) setBoardDialog({ kind: "exists" });
      else setBoardDialog({ kind: "error", message: errText(e, "Could not build the board.") });
    }
    setBoardBusy(false);
  };

  const exportFile = async (ext) => {
    try {
      const { data } = await api.get(`/boards/${boardId}/srs/export.${ext}`, { params: { version: doc.version }, responseType: "blob" });
      download(data, `SRS_v${doc.version}.${ext}`);
    } catch (e) { flash(errText(e, "Download failed.")); }
  };

  const newGeneration = () => { setDescription(doc?.description || description); setQuestions([]); setError(""); setStep("describe"); };

  const TABS = [["srs", "SRS document"], ["req", "Requirements"], ["quality", "Quality checks"], ["diagrams", "Diagrams"], ["analysis", "Analysis"]];
  const issueCount = doc?.issues?.length || 0;

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Page toolbar (global nav lives in the sidebar) */}
      <div className="border-b border-neutral-200 bg-white sticky top-0 z-10 print:hidden">
        <div className="max-w-5xl mx-auto px-6 min-h-14 py-2 flex flex-wrap gap-2 items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold text-neutral-900">SRS</h1>
            <div className="flex gap-1">
              <button onClick={() => loadDemo("hospital")} className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-neutral-300 hover:bg-neutral-100">Hospital demo</button>
              <button onClick={() => loadDemo("ecommerce")} className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-neutral-300 hover:bg-neutral-100">Store demo</button>
              <button onClick={() => loadDemo("university")} className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-neutral-300 hover:bg-neutral-100">University demo</button>
            </div>
          </div>
          {step === "result" && doc && (
            <div className="flex flex-wrap items-center gap-2">
              {versions.length > 1 && (
                <select value={doc.version} onChange={(e) => loadDoc(Number(e.target.value))}
                  className="text-xs border border-neutral-200 rounded-lg px-2 py-1.5 bg-white">
                  {versions.map((v) => <option key={v.id} value={v.version}>Version {v.version}</option>)}
                </select>
              )}
              <button onClick={() => exportFile("md")} className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">.md</button>
              <button onClick={() => exportFile("docx")} className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">Word</button>
              <button onClick={() => { setTab("srs"); setTimeout(() => window.print(), 100); }} className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">PDF / Print</button>
              <button onClick={() => buildBoard("create")} disabled={boardBusy} title={`Create Kanban tasks from SRS version ${doc.version}`}
                className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-900 text-neutral-900 hover:bg-neutral-100 disabled:opacity-50 transition">
                {boardBusy && !boardDialog ? "Building…" : "Generate board"}
              </button>
              <button onClick={newGeneration} className="text-xs font-medium px-3 py-1.5 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 transition">New version</button>
            </div>
          )}
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-6 py-10">
        {step === "loading" && <div className="h-40 bg-white border border-neutral-200 rounded-2xl animate-pulse" />}

        {step === "demo" && demoData && (
          <section className="space-y-5">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <p className="font-semibold text-amber-950">Offline exhibition mode</p>
              <p className="text-sm text-amber-900 mt-1">{demoNotice}</p>
              <button onClick={() => { setDemoData(null); setStep("describe"); }} className="mt-3 text-sm font-medium underline">Return to live project workflow</button>
            </div>
            <div className="bg-white border border-neutral-200 rounded-2xl p-6">
              <h1 className="text-2xl font-semibold">{demoData.title}</h1>
              <p className="text-sm text-neutral-600 mt-2">{demoData.description}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
                <div className="rounded-xl bg-neutral-50 p-3"><p className="text-xs text-neutral-500">Functional requirements</p><p className="text-2xl font-semibold">{demoData.requirements.functional_requirements.length}</p></div>
                <div className="rounded-xl bg-neutral-50 p-3"><p className="text-xs text-neutral-500">UML examples</p><p className="text-2xl font-semibold">{demoData.diagrams.length}</p></div>
                <div className="rounded-xl bg-neutral-50 p-3"><p className="text-xs text-neutral-500">Kanban tasks</p><p className="text-2xl font-semibold">{demoData.board.tasks.length}</p></div>
                <div className="rounded-xl bg-neutral-50 p-3"><p className="text-xs text-neutral-500">Likely estimate</p><p className="text-xl font-semibold">PKR {(demoData.cost.likely).toLocaleString("en-PK")}</p></div>
              </div>
            </div>
            <div className="bg-white border border-neutral-200 rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-3">SRS document</h2>
              <article className="prose max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{demoData.markdown}</ReactMarkdown></article>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              {demoData.diagrams.map((d) => <div key={d.type} className="bg-white border border-neutral-200 rounded-2xl p-5"><h3 className="font-semibold">{d.title}</h3><p className="text-xs text-neutral-500 mt-1">Diagram source preview</p><pre className="text-xs overflow-auto whitespace-pre-wrap bg-neutral-50 rounded-lg p-3 mt-3">{d.mermaid}</pre></div>)}
            </div>
            <div className="bg-white border border-neutral-200 rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-3">Kanban plan</h2>
              <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">{demoData.board.columns.map((col) => <div key={col} className="rounded-xl bg-neutral-50 p-3"><p className="font-medium text-sm">{col}</p>{demoData.board.tasks.filter((t) => t.status === col).map((task) => <div key={task.id} className="bg-white border border-neutral-200 rounded-lg p-2 mt-2 text-xs">{task.title}<p className="text-neutral-500 mt-1">{task.priority} · {task.story_points} points</p></div>)}</div>)}</div>
            </div>
            <div className="bg-white border border-neutral-200 rounded-2xl p-6">
              <h2 className="text-lg font-semibold">Cost estimate (illustrative)</h2>
              <p className="text-sm text-neutral-600 mt-2">Optimistic: PKR {demoData.cost.optimistic.toLocaleString("en-PK")} · Likely: PKR {demoData.cost.likely.toLocaleString("en-PK")} · Pessimistic: PKR {demoData.cost.pessimistic.toLocaleString("en-PK")}</p>
              <p className="text-xs text-amber-800 mt-2">{demoData.cost.disclaimer}</p>
            </div>
          </section>
        )}

        {step === "describe" && <DescribeStep value={description} onChange={setDescription} onNext={fetchQuestions} onSkip={() => startJob(false)} busy={busy} error={error} />}

        {step === "questions" && <QuestionsStep questions={questions} answers={answers} setAnswers={setAnswers}
          onBack={() => setStep("describe")} onGenerate={() => startJob(true)} busy={busy} error={error} />}

        {step === "progress" && <ProgressStep stage={stage} error={jobError} onRetry={() => { setJobError(""); setStep("describe"); }} />}

        {step === "result" && doc && (
          <>
            <div className="flex gap-1 border-b border-neutral-200 mb-6 print:hidden overflow-x-auto">
              {TABS.map(([k, label]) => (
                <button key={k} onClick={() => openTab(k)}
                  className={`px-4 py-2.5 text-sm whitespace-nowrap border-b-2 -mb-px transition ${tab === k ? "border-neutral-900 text-neutral-900 font-medium" : "border-transparent text-neutral-500 hover:text-neutral-900"}`}>
                  {label}{k === "quality" && issueCount > 0 && <span className="ml-1.5 text-[10px] bg-amber-100 text-amber-800 rounded-full px-1.5 py-0.5">{issueCount}</span>}
                </button>
              ))}
            </div>

            {tab === "srs" && (
              <article className="bg-white border border-neutral-200 rounded-2xl p-8 sm:p-10 print:border-0 print:p-0">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{doc.markdown}</ReactMarkdown>
              </article>
            )}
            {tab === "req" && <RequirementsTab req={doc.requirements} onSave={saveEdits} saving={saving} />}
            {tab === "quality" && <QualityTab issues={doc.issues || []} />}
            {/* Mounted on first open, then kept mounted (hidden) so a running diagram job
                keeps polling and neither panel refetches when you switch tabs. */}
            {visited.diagrams && (
              <div className={tab === "diagrams" ? "" : "hidden"}>
                <DiagramsPanel boardId={boardId} srsId={doc.id} version={doc.version} />
              </div>
            )}
            {tab === "analysis" && (
              <ComingSoon
                title="Analysis"
                description="Gap analysis, risk analysis and improvement suggestions for this SRS will appear here."
              />
            )}
          </>
        )}
      </main>

      <BoardDialog state={boardDialog} busy={boardBusy} onClose={() => setBoardDialog(null)}
        onChoose={buildBoard} onOpenBoard={() => navigate(`/boards/${boardId}/kanban`)} />

      {toast && <div className="fixed bottom-5 right-5 z-50 bg-white border border-neutral-200 text-sm font-medium text-neutral-900 px-4 py-2.5 rounded-lg shadow-lg print:hidden">{toast}</div>}
    </div>
  );
}