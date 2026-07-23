import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/axios.js";

function IconBack() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
function IconRefresh() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M13.5 8a5.5 5.5 0 1 1-1.7-4M13.5 3v3.5H10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
function IconCopy() {
  return <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.4" /><path d="M2.5 10.5v-7a1 1 0 0 1 1-1h7" stroke="currentColor" strokeWidth="1.4" /></svg>;
}
function IconBolt() {
  return <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M9 1.5L3 9h4l-1 5.5L13 7H9l0-5.5z" fill="currentColor" /></svg>;
}
function IconWarn() {
  return <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l7 12H1L8 2z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" /><path d="M8 6.5v3M8 11.5h.01" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>;
}
function IconLayers() {
  return <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 3-6 3-6-3 6-3z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M2 8.5l6 3 6-3M2 11.5l6 3 6-3" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg>;
}
function IconSplit() {
  return <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2v5M8 7L4 11M8 7l4 4M4 11v2h0M12 11v2h0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
function IconPlus() {
  return <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" /></svg>;
}
function IconCheck() {
  return <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 8.5l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function SectionCard({ icon, tone, title, children }) {
  return (
    <div className="bg-white border border-neutral-200 rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-7 h-7 rounded-md flex items-center justify-center ${tone.bg} ${tone.text}`}>{icon}</div>
        <h3 className="font-semibold text-neutral-900 text-sm">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function EmptyNote({ children }) {
  return <p className="text-sm text-neutral-400 italic">{children}</p>;
}

function BreakdownItem({ item, onApplied }) {
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);

  const apply = async () => {
    if (!item.task_id || !item.column_id || applying) return;
    setApplying(true);
    try {
      await Promise.all(
        item.subtasks.map((title) =>
          api.post("/tasks/", {
            title,
            description: `Broken down from: ${item.task_title}`,
            priority: "medium",
            column_id: item.column_id,
          })
        )
      );
      setApplied(true);
      onApplied?.(item.subtasks.length);
    } catch {
      // leave applying=false so they can retry
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="border border-neutral-200 rounded-xl p-4">
      <p className="text-sm font-medium text-neutral-900 mb-2">{item.task_title}</p>
      <ul className="space-y-1.5 mb-3">
        {item.subtasks.map((s, i) => (
          <li key={i} className="text-sm text-neutral-600 flex gap-2">
            <span className="text-neutral-300 shrink-0">—</span>{s}
          </li>
        ))}
      </ul>
      {item.task_id ? (
        applied ? (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600">
            <IconCheck /> Added to board
          </span>
        ) : (
          <button
            onClick={apply}
            disabled={applying}
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-neutral-950 text-white hover:bg-neutral-800 disabled:opacity-50 transition"
          >
            <IconPlus /> {applying ? "Adding…" : "Add these subtasks"}
          </button>
        )
      ) : (
        <p className="text-xs text-neutral-400">Couldn't match this to a task on the board.</p>
      )}
    </div>
  );
}

export default function ProjectAnalysis() {
  const { boardId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get(`/boards/${boardId}/analyze`);
      setReport(data);
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
        "Couldn't generate insights for this board right now."
      );
    } finally {
      setLoading(false);
    }
  }, [boardId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const copyDigest = async () => {
    if (!report?.digest) return;
    try {
      await navigator.clipboard.writeText(report.digest);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard blocked — no-op, button just won't confirm
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b border-neutral-200 bg-white sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
          <button
            onClick={() => navigate(`/boards/${boardId}`)}
            className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-900 transition"
          >
            <IconBack /> Back to board
          </button>
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition disabled:opacity-50"
          >
            <IconRefresh /> {loading ? "Thinking…" : "Refresh insights"}
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {loading && (
          <div className="space-y-5">
            <div className="h-8 w-64 bg-neutral-200/70 rounded animate-pulse" />
            {[1, 2, 3, 4].map(i => <div key={i} className="h-28 bg-white border border-neutral-200 rounded-2xl animate-pulse" />)}
          </div>
        )}

        {!loading && error && (
          <div className="text-center py-20">
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3 inline-block">{error}</p>
            <div className="mt-4">
              <button onClick={load} className="text-sm font-medium text-neutral-900 underline underline-offset-2">Try again</button>
            </div>
          </div>
        )}

        {!loading && !error && report && (
          <>
            <div className="mb-8">
              <p className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1.5">Project insights</p>
              <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">{report.board_name}</h1>
              <div className="flex items-center gap-4 mt-3 text-xs text-neutral-500">
                <span>{report.total_tasks} task{report.total_tasks === 1 ? "" : "s"}</span>
                <span>{report.total_columns} column{report.total_columns === 1 ? "" : "s"}</span>
                <span>{report.completion_percent}% complete</span>
              </div>
            </div>

            <div className="space-y-5">
              <SectionCard icon={<IconLayers />} tone={{ bg: "bg-neutral-100", text: "text-neutral-700" }} title="Status digest — copy and share">
                <p className="text-sm text-neutral-600 leading-relaxed mb-3 whitespace-pre-wrap">{report.digest}</p>
                <button
                  onClick={copyDigest}
                  className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition"
                >
                  <IconCopy /> {copied ? "Copied!" : "Copy"}
                </button>
              </SectionCard>

              <SectionCard icon={<IconBolt />} tone={{ bg: "bg-amber-50", text: "text-amber-600" }} title="Do this next">
                <p className="text-sm font-medium text-neutral-900 mb-1.5">{report.next_action?.action}</p>
                <p className="text-sm text-neutral-500 leading-relaxed">{report.next_action?.reason}</p>
              </SectionCard>

              <SectionCard icon={<IconWarn />} tone={{ bg: "bg-red-50", text: "text-red-600" }} title="Stuck points">
                {report.stuck_points?.length ? (
                  <ul className="space-y-2">
                    {report.stuck_points.map((s, i) => (
                      <li key={i} className="text-sm text-neutral-600 flex gap-2"><span className="text-neutral-300 shrink-0">—</span>{s}</li>
                    ))}
                  </ul>
                ) : <EmptyNote>Nothing looks stuck right now.</EmptyNote>}
              </SectionCard>

              <SectionCard icon={<IconLayers />} tone={{ bg: "bg-blue-50", text: "text-blue-600" }} title="Possible duplicates">
                {report.duplicates?.length ? (
                  <div className="space-y-3">
                    {report.duplicates.map((d, i) => (
                      <div key={i} className="text-sm">
                        <p className="font-medium text-neutral-900">{d.titles.join(" · ")}</p>
                        <p className="text-neutral-500 mt-0.5">{d.note}</p>
                      </div>
                    ))}
                  </div>
                ) : <EmptyNote>No overlapping tasks found.</EmptyNote>}
              </SectionCard>

              <SectionCard icon={<IconSplit />} tone={{ bg: "bg-emerald-50", text: "text-emerald-600" }} title="Break these down">
                {report.breakdowns?.length ? (
                  <div className="space-y-3">
                    {report.breakdowns.map((b, i) => (
                      <BreakdownItem
                        key={i}
                        item={b}
                        onApplied={(n) => setToast(`Added ${n} subtask${n === 1 ? "" : "s"} to the board.`)}
                      />
                    ))}
                  </div>
                ) : <EmptyNote>No tasks look like they need splitting up.</EmptyNote>}
              </SectionCard>
            </div>
          </>
        )}
      </main>

      {toast && (
        <div className="fixed bottom-5 right-5 z-50 bg-white border border-neutral-200 text-sm font-medium text-neutral-900 px-4 py-2.5 rounded-lg shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
