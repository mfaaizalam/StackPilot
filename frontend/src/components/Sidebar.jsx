import { useEffect, useState } from "react";
import { NavLink, useLocation, useMatch, useNavigate } from "react-router-dom";
import { useBoards } from "../api/queries.js";
import { queryClient } from "../api/queryClient.js";

// ── Icons ────────────────────────────────────────────────────────────────────
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
function IconCosting() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="7.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12.5 7.5c-.4-.8-1.4-1.2-2.5-1.2-1.4 0-2.4.7-2.4 1.8 0 2.4 5 1.1 5 3.6 0 1.1-1.1 1.9-2.6 1.9-1.2 0-2.2-.5-2.6-1.4M10 4.8v1.5M10 13.7v1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
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
function IconAnalysis() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M3.5 16.5V10M8 16.5V4.5M12.5 16.5V8M17 16.5V3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function IconSettings() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M3 5.5h6M13 5.5h4M3 10h2M9 10h8M3 14.5h9M16 14.5h1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="11" cy="5.5" r="1.7" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="7" cy="10" r="1.7" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="14" cy="14.5" r="1.7" stroke="currentColor" strokeWidth="1.5" />
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

const SECTIONS = [
  { to: "kanban", label: "Kanban Board", icon: <IconKanban /> },
  { to: "srs", label: "SRS", icon: <IconSrs /> },
  { to: "diagrams", label: "Diagrams", icon: <IconDiagrams /> },
  { to: "costing", label: "Costing", icon: <IconCosting /> },
  { to: "sdd", label: "SDD", icon: <IconSdd />, soon: true },
  { to: "analysis", label: "Analysis", icon: <IconAnalysis />, soon: true },
  { to: "settings", label: "Settings", icon: <IconSettings />, soon: true },
];
const SECTION_KEYS = SECTIONS.map((s) => s.to);

export default function Sidebar({ open, onClose }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const { data: boards = [] } = useBoards();
  const [switcherOpen, setSwitcherOpen] = useState(false);

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
  const currentSection = SECTION_KEYS.includes(seg) ? seg : "kanban";

  const switchTo = (board) => {
    setSwitcherOpen(false);
    navigate(`/boards/${board.id}/${currentSection}`);
    onClose?.();
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("lastBoardId");
    queryClient.clear(); // don't leak cached data to the next user on this browser
    navigate("/login");
  };

  const linkBase =
    "flex items-center gap-2.5 text-sm px-3 py-2 rounded-lg transition";

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-neutral-950/30 md:hidden print:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed left-0 top-0 bottom-0 z-40 w-60 bg-white border-r border-neutral-200 flex flex-col transition-transform duration-200 print:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0`}
      >
        {/* Logo */}
        <div className="h-14 px-4 flex items-center gap-2 font-semibold tracking-tight border-b border-neutral-100 shrink-0">
          <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center font-bold text-sm">
            S
          </div>
          StackPilot
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* Projects row (current project + switcher) */}
          <div className="relative">
            <p className="px-1 mb-1.5 text-[11px] text-neutral-400 font-medium uppercase tracking-wide">
              Projects
            </p>
            <button
              onClick={() => setSwitcherOpen((v) => !v)}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border border-neutral-200 bg-neutral-50 hover:bg-neutral-100 transition text-left"
            >
              <span className="text-neutral-500 shrink-0">
                <IconFolder />
              </span>
              <span className="flex-1 min-w-0 text-sm font-medium text-neutral-900 truncate">
                {currentBoard?.name || "Select a project"}
              </span>
              <span className="text-neutral-400 shrink-0">
                <IconChevron />
              </span>
            </button>

            {switcherOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setSwitcherOpen(false)} />
                <div className="absolute left-0 right-0 top-full mt-1 z-20 bg-white border border-neutral-200 rounded-lg shadow-lg py-1">
                  <div className="max-h-64 overflow-y-auto">
                    {boards.length === 0 ? (
                      <p className="px-3 py-2 text-xs text-neutral-400">No projects yet.</p>
                    ) : (
                      boards.map((b) => (
                        <button
                          key={b.id}
                          onClick={() => switchTo(b)}
                          className={`w-full text-left px-3 py-2 text-sm truncate hover:bg-neutral-50 transition ${
                            String(b.id) === String(activeId)
                              ? "font-medium text-neutral-900 bg-neutral-50"
                              : "text-neutral-600"
                          }`}
                        >
                          {b.name}
                        </button>
                      ))
                    )}
                  </div>
                  <div className="border-t border-neutral-100 mt-1 pt-1">
                    <button
                      onClick={() => {
                        setSwitcherOpen(false);
                        navigate("/boards");
                        onClose?.();
                      }}
                      className="w-full text-left px-3 py-2 text-xs text-neutral-500 hover:text-neutral-900 hover:bg-neutral-50 transition"
                    >
                      Manage projects / New project
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Section links */}
          <nav className="space-y-1">
            {SECTIONS.map(({ to, label, icon, soon }) =>
              activeId ? (
                <NavLink
                  key={to}
                  to={`/boards/${activeId}/${to}`}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `${linkBase} ${
                      isActive
                        ? "bg-neutral-100 text-neutral-900 font-medium"
                        : "text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100"
                    }`
                  }
                >
                  {icon}
                  {label}
                  {soon && (
                    <span className="ml-auto text-[10px] font-medium text-neutral-400 bg-neutral-100 border border-neutral-200 rounded-full px-1.5 py-0.5">
                      Soon
                    </span>
                  )}
                </NavLink>
              ) : (
                <span
                  key={to}
                  title="Select a project first"
                  className={`${linkBase} text-neutral-300 cursor-not-allowed`}
                >
                  {icon}
                  {label}
                  {soon && (
                    <span className="ml-auto text-[10px] font-medium text-neutral-300 bg-neutral-50 border border-neutral-200 rounded-full px-1.5 py-0.5">
                      Soon
                    </span>
                  )}
                </span>
              )
            )}
          </nav>
        </div>

        {/* User + sign out */}
        <div className="border-t border-neutral-100 p-3 shrink-0">
          <div className="flex items-center gap-2.5 mb-3 px-1">
            <div className="w-9 h-9 rounded-full bg-neutral-900 text-white flex items-center justify-center font-semibold text-sm shrink-0">
              {user?.name?.charAt(0) || "U"}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium leading-none truncate">{user?.name || "User"}</p>
              <p className="text-xs text-neutral-500 mt-1 truncate">{user?.email || ""}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full text-sm px-3 py-2 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition"
          >
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}