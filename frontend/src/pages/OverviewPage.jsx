import { Link, useParams } from "react-router-dom";
import { useBoards, useLatestSrs } from "../api/queries.js";

// Desktop: 3x2 snake  (1 → 2 → 3 ↓ 4 ← 5, project summary fills the last cell).
// Mobile: one column, top to bottom. The grid is placed with CSS classes
// (ov-at-COLUMN-ROW) so the DOM order stays the mobile reading order.
const OVERVIEW_STYLES = `
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;600&display=swap');
.sp-hand { font-family: 'Caveat', 'Segoe Print', 'Bradley Hand', cursive; }

.ov-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 4px; }
.ov-arrow { display: flex; align-items: center; justify-content: center; height: 36px; }
.ov-arrow svg { transform: rotate(90deg); }

.ov-card { transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
.ov-card:hover { transform: translateY(-3px); box-shadow: 0 14px 22px -12px rgba(0,0,0,.35); }

@media (min-width: 768px) {
  .ov-grid { grid-template-columns: minmax(0,1fr) 56px minmax(0,1fr) 56px minmax(0,1fr); gap: 0; }
  .ov-arrow { height: auto; min-height: 36px; }
  .ov-arrow.r svg { transform: none; }
  .ov-arrow.d svg { transform: rotate(90deg); }
  .ov-arrow.l svg { transform: rotate(180deg); }
  .ov-arrow.d { padding: 10px 0; }
  .ov-at-1-1 { grid-column: 1; grid-row: 1; } .ov-at-2-1 { grid-column: 2; grid-row: 1; }
  .ov-at-3-1 { grid-column: 3; grid-row: 1; } .ov-at-4-1 { grid-column: 4; grid-row: 1; }
  .ov-at-5-1 { grid-column: 5; grid-row: 1; } .ov-at-5-2 { grid-column: 5; grid-row: 2; }
  .ov-at-5-3 { grid-column: 5; grid-row: 3; } .ov-at-4-3 { grid-column: 4; grid-row: 3; }
  .ov-at-3-3 { grid-column: 3; grid-row: 3; } .ov-at-1-3 { grid-column: 1; grid-row: 3; }
}
@media (prefers-reduced-motion: reduce) { .ov-card { transition: none; } .ov-card:hover { transform: none; } }
`;

const STAGES = [
  { key: "scope",          step: 1, name: "Scope",          to: "scope",    title: "Project Scope",       blurb: "Name the project and describe what you are building.", accent: "#3B8EEA", at: "ov-at-1-1" },
  { key: "requirements",   step: 2, name: "Requirements",   to: "srs",      title: "SRS Document",        blurb: "Questions, requirements and the IEEE-style SRS.",      accent: "#8E7CC3", at: "ov-at-3-1" },
  { key: "design",         step: 3, name: "Design",         to: "sdd",      title: "Design Document",     blurb: "Software design document built from the SRS.",         accent: "#E4568C", at: "ov-at-5-1", extra: { to: "diagrams", label: "Diagrams" } },
  { key: "implementation", step: 4, name: "Implementation", to: "kanban",   title: "Kanban Board",        blurb: "Turn requirements into tasks and track the work.",     accent: "#F0A020", at: "ov-at-5-3", extra: { to: "timeline", label: "Gantt Chart" } },
  { key: "deployment",     step: 5, name: "Deployment",     to: "document", title: "Deployment Document", blurb: "Plan and document how the product goes live.",         accent: "#2FB86B", at: "ov-at-3-3" },
];

// Connectors between stages: direction is only used on desktop.
const ARROWS = [
  { dir: "r", at: "ov-at-2-1" },
  { dir: "r", at: "ov-at-4-1" },
  { dir: "d", at: "ov-at-5-2" },
  { dir: "l", at: "ov-at-4-3" },
];

function Arrow({ dir, at }) {
  return (
    <div className={`ov-arrow ${dir} ${at} text-ink-muted/60`} aria-hidden="true">
      <svg width="40" height="16" viewBox="0 0 40 16" fill="none">
        <path d="M2 8h30" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="4 4" />
        <path d="M28 3l7 5-7 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function StageCard({ stage, boardId, hint }) {
  const { accent } = stage;
  return (
    <div
      className={`ov-card relative flex flex-col rounded-2xl bg-surface p-4 ${stage.at}`}
      style={{ border: `1px solid ${accent}40`, borderTop: `5px solid ${accent}` }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${accent}99`)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = `${accent}40`)}
    >
      {/* Faint step numeral */}
      <span
        className="sp-hand absolute top-1 right-4 text-7xl font-semibold leading-none select-none pointer-events-none"
        style={{ color: `${accent}22` }}
        aria-hidden="true"
      >
        {stage.step}
      </span>

      <div className="flex items-center gap-2">
        <span
          className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold"
          style={{ background: `${accent}26`, color: accent }}
        >
          {stage.step}
        </span>
        <span className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: accent }}>
          {stage.name}
        </span>
      </div>

      {/* The title link stretches over the whole card, so the card is the shortcut */}
      <Link
        to={`/boards/${boardId}/${stage.to}`}
        className="sp-hand mt-2 text-[28px] font-semibold leading-[1.05] text-ink focus:outline-none after:absolute after:inset-0 after:rounded-2xl focus-visible:after:ring-2"
        style={{ "--tw-ring-color": accent }}
      >
        {stage.title}
      </Link>
      <p className="mt-1.5 text-xs text-ink-muted leading-relaxed">{stage.blurb}</p>

      <div className="mt-auto pt-4 flex items-center gap-2 flex-wrap">
        {hint ? (
          <span
            className="inline-flex items-center gap-1.5 text-[11px] font-medium rounded-full px-2 py-0.5"
            style={{ background: `${accent}1F`, color: accent }}
          >
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: accent }} />
            {hint}
          </span>
        ) : null}
        {stage.extra && (
          <Link
            to={`/boards/${boardId}/${stage.extra.to}`}
            className="relative z-10 text-[11px] font-medium rounded-full px-2 py-0.5 border hover:bg-surface-2 transition"
            style={{ borderColor: `${accent}77`, color: accent }}
          >
            {stage.extra.label}
          </Link>
        )}
        <span className="ml-auto text-xs font-semibold" style={{ color: accent }}>Open →</span>
      </div>
    </div>
  );
}

function SummaryCard({ board, boardId }) {
  return (
    <div className="ov-at-1-3 flex flex-col rounded-2xl border-2 border-dashed border-ink-muted/30 p-4">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted/80">Project</span>
      <p className="sp-hand mt-1 text-[28px] font-semibold leading-[1.05] text-ink break-words">
        {board?.name || "Your project"}
      </p>
      {board?.description?.trim() ? (
        <p className="mt-1.5 text-xs text-ink-muted leading-relaxed line-clamp-4">{board.description}</p>
      ) : (
        <p className="mt-1.5 text-xs text-ink-muted/70 italic">No description yet.</p>
      )}
      <Link
        to={`/boards/${boardId}/scope`}
        className="mt-auto pt-4 text-xs font-medium text-ink-muted hover:text-ink underline underline-offset-2"
      >
        Edit in Project Scope
      </Link>
    </div>
  );
}

export default function OverviewPage() {
  const { boardId } = useParams();
  const { data: boards = [] } = useBoards();
  const board = boards.find((b) => String(b.id) === String(boardId));
  const srs = useLatestSrs(boardId);

  // Optional status hints. If the backend is down they simply disappear.
  const hints = {
    scope: board ? (board.description?.trim() ? "Description added" : "Add a description") : "",
    requirements: srs.data?.version ? `SRS v${srs.data.version}` : srs.isError ? "Not generated yet" : "",
  };

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col">
      <style>{OVERVIEW_STYLES}</style>

      <div className="border-b border-line bg-surface sticky top-0 z-10 shrink-0">
        <div className="px-3 sm:px-6 py-3">
          <h1 className="text-lg font-semibold tracking-tight truncate">Overview</h1>
          <p className="text-xs text-ink-muted mt-0.5 truncate">
            Follow the software development life cycle. Click a card to jump in.
          </p>
        </div>
      </div>

      <div className="flex-1 flex items-center">
        <div className="ov-grid w-full max-w-5xl mx-auto p-4 sm:p-8">
          <SummaryCard board={board} boardId={boardId} />
          {STAGES.map((stage, i) => (
            <FragmentWithArrow key={stage.key} index={i}>
              <StageCard stage={stage} boardId={boardId} hint={hints[stage.key]} />
            </FragmentWithArrow>
          ))}
        </div>
      </div>
    </div>
  );
}

// Renders the connector that leads INTO this stage (none for the first one),
// followed by the stage card, so mobile order is: summary, 1, ↓, 2, ↓, 3 ...
function FragmentWithArrow({ index, children }) {
  const arrow = index > 0 ? ARROWS[index - 1] : null;
  return (
    <>
      {arrow && <Arrow dir={arrow.dir} at={arrow.at} />}
      {children}
    </>
  );
}