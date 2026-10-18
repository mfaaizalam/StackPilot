import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api/axios.js";
import DiagramCard from "./DiagramCard.jsx";

const TYPES = [
  ["usecase", "Use case"],
  ["class", "Class"],
  ["sequence", "Sequence"],
  ["activity", "Activity"],
  ["state", "State"],
  ["deployment", "Deployment"],
];

const errText = (e, fallback = "Something went wrong. Please try again.") => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  return fallback;
};

function Spinner() {
  return <span className="inline-block w-4 h-4 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" />;
}

export default function DiagramsPanel({ boardId, srsId, version }) {
  const [diagrams, setDiagrams] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [active, setActive] = useState("usecase");
  const [progress, setProgress] = useState(null); // {done,total} while a job runs
  const [error, setError] = useState("");
  const pollRef = useRef(null);
  const srsRef = useRef(srsId);
  srsRef.current = srsId;

  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/boards/${boardId}/srs/diagrams`, { params: { srs_id: srsId } });
      if (data.srs_id !== srsRef.current) return;
      setDiagrams(data.diagrams);
    } catch (e) { setError(errText(e)); }
    setLoaded(true);
  }, [boardId, srsId]);

  // reload when the SRS version changes; stop any poll that belonged to the old version
  useEffect(() => { stopPolling(); setProgress(null); setError(""); setLoaded(false); load(); return stopPolling; }, [load]);

  // keep the selected sub-tab pointing at something that exists
  useEffect(() => {
    if (diagrams.length && !diagrams.some((d) => d.type === active)) setActive(diagrams[0].type);
  }, [diagrams, active]);

  const generate = async () => {
    setError(""); setProgress({ done: 0, total: 0 });
    try {
      const { data } = await api.post(`/boards/${boardId}/srs/diagrams/generate`, { srs_id: srsId });
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const { data: st } = await api.get(`/boards/${boardId}/srs/diagrams/jobs/${data.job_id}`);
          const m = /^(\d+)\/(\d+)$/.exec(st.stage || "");
          if (m) setProgress({ done: +m[1], total: +m[2] });
          if (m) load(); // diagrams appear one by one as they finish
          if (st.status === "done") { stopPolling(); setProgress(null); load(); }
          if (st.status === "failed") { stopPolling(); setProgress(null); setError(st.error || "Diagram generation failed."); load(); }
        } catch (e) {
          if ([401, 404].includes(e?.response?.status)) { stopPolling(); setProgress(null); setError(errText(e)); }
        }
      }, 2000);
    } catch (e) { setProgress(null); setError(errText(e)); }
  };

  const counts = Object.fromEntries(TYPES.map(([k]) => [k, diagrams.filter((d) => d.type === k).length]));
  const shown = diagrams.filter((d) => d.type === active);
  const stale = diagrams.some((d) => d.stale);
  const running = progress !== null;
  const pct = progress?.total ? Math.round((progress.done / progress.total) * 100) : 4;

  if (!loaded) return <div className="h-40 bg-white border border-neutral-200 rounded-2xl animate-pulse print:hidden" />;

  return (
    <div className="print:hidden">
      {error && <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">{error}</p>}

      {running && (
        <div className="mb-5 bg-white border border-neutral-200 rounded-2xl px-5 py-4">
          <div className="flex items-center gap-2 text-sm text-neutral-700 mb-2.5">
            <Spinner /> Drawing diagrams{progress.total ? ` (${progress.done} of ${progress.total})` : "…"}
          </div>
          <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden"><div className="h-full bg-neutral-900 transition-all duration-500" style={{ width: `${pct}%` }} /></div>
        </div>
      )}

      {!diagrams.length && !running ? (
        <div className="bg-white border border-neutral-200 rounded-2xl px-8 py-14 text-center">
          <h2 className="text-lg font-semibold text-neutral-900">Turn this SRS into UML diagrams</h2>
          <p className="text-sm text-neutral-500 mt-2 max-w-md mx-auto">
            We draw a use case diagram, a class diagram, sequence and activity diagrams for your most important use cases, and state diagrams for anything with a lifecycle, and a deployment diagram of the system. Version {version}.
          </p>
          <button onClick={generate} className="mt-6 text-sm font-medium px-5 py-2.5 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 transition">Generate diagrams</button>
        </div>
      ) : (
        <>
          {stale && !running && (
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3 text-sm bg-amber-50 border border-amber-100 text-amber-800 rounded-xl px-4 py-3">
              <span>The requirements changed after these diagrams were drawn.</span>
              <button onClick={generate} className="text-xs font-medium px-3 py-1.5 rounded-lg bg-amber-800 text-white hover:bg-amber-900 transition">Regenerate</button>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
            <div className="flex flex-wrap gap-2">
              {TYPES.filter(([k]) => counts[k] > 0).map(([k, label]) => (
                <button key={k} onClick={() => setActive(k)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition ${active === k ? "bg-neutral-950 text-white border-neutral-950" : "bg-white text-neutral-700 border-neutral-200 hover:bg-neutral-100"}`}>
                  {label} <span className="opacity-60">{counts[k]}</span>
                </button>
              ))}
            </div>
            {!running && !stale && (
              <button onClick={generate} className="text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">Regenerate all</button>
            )}
          </div>

          <div className="space-y-5">
            {shown.map((d) => <DiagramCard key={d.id} d={d} />)}
          </div>
        </>
      )}
    </div>
  );
}
