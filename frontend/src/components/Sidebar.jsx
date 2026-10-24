import { useEffect, useState } from "react";
import { NavLink, useLocation, useMatch, useNavigate } from "react-router-dom";
import { useBoards } from "../api/queries.js";

// ── Icons ────────────────────────────────────────────────────────────────────
function IconOverview() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <rect x="2.5" y="7.5" width="4" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="13.5" y="7.5" width="4" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6.5 10h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function IconScope() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
function IconGithub() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="7.5" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="10" r="1.6" fill="currentColor" />
    </svg>
  );
}
function IconChevron() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3.5 5.5L7 9l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconKanban() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <rect x="2" y="3" width="4" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <rect x="8" y="3" width="4" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <rect x="14" y="3" width="4" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
function IconSrs() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M5 2.5h7l3.5 3.5V17a.5.5 0 01-.5.5H5a.5.5 0 01-.5-.5V3a.5.5 0 01.5-.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M7.5 10h5M7.5 13h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function IconDiagrams() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <rect x="7.5" y="2.5" width="5" height="4" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="2.5" y="13.5" width="5" height="4" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="12.5" y="13.5" width="5" height="4" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 6.5v3.5M5 13.5V10h10v3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconDeploy() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M5 2.5h7l3.5 3.5v11a1 1 0 0 1-1 1h-9.5a1 1 0 0 1-1-1v-13.5a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M7.5 11h5M7.5 14h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function IconGantt() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M3 5h7M6 10h8M9 15h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
function IconSdd() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M10 2.5l7.5 3.8L10 10 2.5 6.3 10 2.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M2.5 10L10 13.8 17.5 10M2.5 13.7L10 17.5l7.5-3.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconFolder() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M2.5 5.5a1.5 1.5 0 011.5-1.5h3.2l1.8 2H16a1.5 1.5 0 011.5 1.5v7A1.5 1.5 0 0116 16H4a1.5 1.5 0 01-1.5-1.5v-9z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

const OVERVIEW = { to: "overview", label: "Overview", icon: <IconOverview /> };
const SETTINGS_KEY = "settings"; // route still exists; reached from the topbar menu

const GROUPS = [
  {
    key: "pm",
    label: "Project Manager",
    items: [
      { to: "kanban",        label: "Kanban Board", icon: <IconKanban /> },
      { to: "timeline",      label: "Gantt Chart",  icon: <IconGantt /> },
      { to: "github-issues", label: "GitHub Issues", icon: <IconGithub />, soon: true },
    ],
  },
  {
    key: "tech",
    label: "Technical Manager",
    items: [
      { to: "scope",    label: "Project Scope",       icon: <IconScope /> },
      { to: "srs",      label: "SRS Document",        icon: <IconSrs /> },
      { to: "diagrams", label: "Diagrams",            icon: <IconDiagrams /> },
      { to: "sdd",      label: "Design Document",     icon: <IconSdd /> },
      { to: "document", label: "Deployment Document", icon: <IconDeploy /> },
    ],
  },
];

const SECTION_KEYS = [
  OVERVIEW.to,
  SETTINGS_KEY,
  ...GROUPS.flatMap((g) => g.items.map((i) => i.to)),
];

export default function Sidebar({ open, onClose }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: boards = [] } = useBoards();
  const [switcherOpen, setSwitcherOpen] = useState(false);

  // Collapsed state per group, remembered across visits.
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("sidebarCollapsed") || "{}");
    } catch {
      return {};
    }
  });
  const toggleGroup = (key) =>
    setCollapsed((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      localStorage.setItem("sidebarCollapsed", JSON.stringify(next));
      return next;
    });

  // Current project: from the URL when inside a project, otherwise the last one used.
  const match = useMatch("/boards/:boardId/*");
  const urlBoardId = match?.params?.boardId;

  useEffect(() => {
    if (urlBoardId) localStorage.setItem("lastBoardId", String(urlBoardId));
  }, [urlBoardId]);

  const storedId = localStorage.getItem("lastBoardId");
  const currentBoard =
    boards.find((b) => String(b.id) === String(urlBoardId ?? storedId)) || null;
  const activeId = urlBoardId ?? currentBoard?.id ?? null;

  // Keep the user in the same section when switching projects.
  const seg = location.pathname.split("/")[3];
  const currentSection = SECTION_KEYS.includes(seg) ? seg : "overview";

  // Auto-expand the group that contains the page being viewed.
  useEffect(() => {
    const g = GROUPS.find((grp) => grp.items.some((i) => i.to === seg));
    if (g) setCollapsed((prev) => (prev[g.key] ? { ...prev, [g.key]: false } : prev));
  }, [seg]);

  const switchTo = (board) => {
    setSwitcherOpen(false);
    navigate(`/boards/${board.id}/${currentSection}`);
    onClose?.();
  };

  const linkBase =
    "flex items-center gap-2 text-[13px] px-2.5 py-1.5 rounded-md transition";

  const renderItem = ({ to, label, icon, soon }) =>
    activeId ? (
      <NavLink
        key={to}
        to={`/boards/${activeId}/${to}`}
        onClick={onClose}
        className={({ isActive }) =>
          `${linkBase} ${
            isActive
              ? "bg-surface-2 text-ink font-medium"
              : "text-ink-muted hover:text-ink hover:bg-surface-2"
          }`
        }
      >
        {icon}
        {label}
        {soon && (
          <span className="ml-auto text-[10px] font-medium text-ink-muted/70 bg-surface-2 border border-line rounded-full px-1.5 py-0.5">
            Soon
          </span>
        )}
      </NavLink>
    ) : (
      <span
        key={to}
        title="Select a project first"
        className={`${linkBase} text-ink-muted/50 cursor-not-allowed`}
      >
        {icon}
        {label}
        {soon && (
          <span className="ml-auto text-[10px] font-medium text-ink-muted/50 bg-surface-2 border border-line rounded-full px-1.5 py-0.5">
            Soon
          </span>
        )}
      </span>
    );

  return (
    <>
      {/* Mobile backdrop: z-[35] sits above the topbar (z-30), below the drawer (z-40) */}
      {open && (
        <div
          className="fixed inset-0 z-[35] bg-overlay/50 md:hidden print:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed left-0 top-0 bottom-0 z-40 w-60 bg-canvas text-ink border-r border-line flex flex-col transition-transform duration-200 print:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0`}
      >
        {/* Logo */}
        <div className="h-12 px-4 flex items-center gap-2 font-semibold tracking-tight border-b border-line shrink-0">
          <div className="w-7 h-7 rounded-md bg-brand text-brand-fg flex items-center justify-center font-bold text-sm">
            S
          </div>
          StackPilot
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {/* Projects row (current project + switcher) */}
          <div className="relative">
            <p className="px-1 mb-1 text-[10px] text-ink-muted/70 font-medium uppercase tracking-wide">
              Projects
            </p>
            <button
              onClick={() => setSwitcherOpen((v) => !v)}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-line bg-surface hover:bg-surface-2 transition text-left"
            >
              <span className="text-ink-muted shrink-0">
                <IconFolder />
              </span>
              <span className="flex-1 min-w-0 text-[13px] font-medium text-ink truncate">
                {currentBoard?.name || "Select a project"}
              </span>
              <span className="text-ink-muted/70 shrink-0">
                <IconChevron />
              </span>
            </button>

            {switcherOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setSwitcherOpen(false)} />
                <div className="absolute left-0 right-0 top-full mt-1 z-20 bg-surface border border-line rounded-lg shadow-lg py-1">
                  <div className="max-h-64 overflow-y-auto">
                    {boards.length === 0 ? (
                      <p className="px-3 py-2 text-xs text-ink-muted/70">No projects yet.</p>
                    ) : (
                      boards.map((b) => (
                        <button
                          key={b.id}
                          onClick={() => switchTo(b)}
                          className={`w-full text-left px-3 py-1.5 text-[13px] truncate hover:bg-surface-2 transition ${
                            String(b.id) === String(activeId)
                              ? "font-medium text-ink bg-surface-2"
                              : "text-ink-muted"
                          }`}
                        >
                          {b.name}
                        </button>
                      ))
                    )}
                  </div>
                  <div className="border-t border-line mt-1 pt-1">
                    <button
                      onClick={() => {
                        setSwitcherOpen(false);
                        navigate("/boards");
                        onClose?.();
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs text-ink-muted hover:text-ink hover:bg-surface-2 transition"
                    >
                      Manage projects / New project
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Section links */}
          <nav className="space-y-0.5">
            {renderItem(OVERVIEW)}

            {GROUPS.map((group) => {
              const isCollapsed = !!collapsed[group.key];
              return (
                <div key={group.key} className="pt-2">
                  <button
                    onClick={() => toggleGroup(group.key)}
                    aria-expanded={!isCollapsed}
                    className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-ink-muted/70 hover:text-ink transition"
                  >
                    {group.label}
                    <span
                      className={`transition-transform duration-150 ${
                        isCollapsed ? "-rotate-90" : ""
                      }`}
                    >
                      <IconChevron />
                    </span>
                  </button>
                  {!isCollapsed && (
                    <div className="mt-0.5 ml-3 pl-2 border-l border-line space-y-0.5">
                      {group.items.map(renderItem)}
                    </div>
                  )}
                </div>
              );
            })}
          </nav>
        </div>
      </aside>
    </>
  );
}