import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { queryClient } from "../api/queryClient.js";
import useActiveBoardId from "../hooks/useActiveBoardId.js";
import useTheme from "../hooks/useTheme.js";

// ── Icons ────────────────────────────────────────────────────────────────────
const Svg = ({ size = 16, children }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none">{children}</svg>
);
const IconMenu = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
    <path d="M3 5h12M3 9h12M3 13h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);
const IconSearch = () => (
  <Svg size={14}>
    <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5" />
    <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </Svg>
);
const IconSparkle = () => (
  <Svg>
    <path d="M8 1.5l1.1 3.4L12.5 6l-3.4 1.1L8 10.5 6.9 7.1 3.5 6l3.4-1.1L8 1.5z" fill="currentColor" />
    <path d="M12.5 10.5l.5 1.5 1.5.5-1.5.5-.5 1.5-.5-1.5-1.5-.5 1.5-.5.5-1.5z" fill="currentColor" />
  </Svg>
);
const IconChevron = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M3.5 5.5L7 9l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconPalette = () => (
  <Svg>
    <path d="M8 2a6 6 0 100 12c1 0 1.5-.7 1.5-1.4 0-.9-.8-1.2-.8-2 0-.7.6-1.1 1.3-1.1H11a3 3 0 003-3C14 4.2 11.3 2 8 2z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
    <circle cx="5" cy="7" r=".8" fill="currentColor" /><circle cx="8" cy="5" r=".8" fill="currentColor" />
  </Svg>
);
const IconSettings = () => (
  <Svg>
    <path d="M2.5 4.5h4M10.5 4.5h3M2.5 8h1.5M7.5 8h6M2.5 11.5h6M12 11.5h1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    <circle cx="8.5" cy="4.5" r="1.5" stroke="currentColor" strokeWidth="1.3" />
    <circle cx="5.5" cy="8" r="1.5" stroke="currentColor" strokeWidth="1.3" />
    <circle cx="10.5" cy="11.5" r="1.5" stroke="currentColor" strokeWidth="1.3" />
  </Svg>
);
const IconLogout = () => (
  <Svg>
    <path d="M6.5 2.5h-3v11h3M10 5l3 3-3 3M13 8H6.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);
const IconSun = () => (
  <Svg>
    <circle cx="8" cy="8" r="2.8" stroke="currentColor" strokeWidth="1.3" />
    <path d="M8 1.5v1.8M8 12.7v1.8M1.5 8h1.8M12.7 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M12.6 3.4l-1.3 1.3M4.7 11.3l-1.3 1.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
  </Svg>
);
const IconMoon = () => (
  <Svg>
    <path d="M13.5 9.6A5.8 5.8 0 016.4 2.5a5.8 5.8 0 107.1 7.1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
  </Svg>
);
const IconMonitor = () => (
  <Svg>
    <rect x="2" y="2.5" width="12" height="8.5" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
    <path d="M5.5 13.5h5M8 11v2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
  </Svg>
);

const THEME_OPTIONS = [
  { value: "system", label: "System", icon: <IconMonitor /> },
  { value: "light", label: "Light", icon: <IconSun /> },
  { value: "dark", label: "Dark", icon: <IconMoon /> },
];

// ── Searchable features ──────────────────────────────────────────────────────
// `to` is the section under /boards/:boardId/ unless `absolute` is set.
const NAV_ITEMS = [
  { label: "Overview",             to: "overview",      group: "General",           keywords: "home sdlc flowchart dashboard" },
  { label: "Kanban Board",         to: "kanban",        group: "Project Manager",   keywords: "tasks notes cards backlog columns board" },
  { label: "Gantt Chart",          to: "timeline",      group: "Project Manager",   keywords: "timeline schedule phases activities budget finance" },
  { label: "GitHub Issues",        to: "github-issues", group: "Project Manager",   keywords: "git issues sync", soon: true },
  { label: "Project Scope",        to: "scope",         group: "Technical Manager", keywords: "name description project details" },
  { label: "SRS Document",         to: "srs",           group: "Technical Manager", keywords: "requirements software requirement specification studio" },
  { label: "Diagrams",             to: "diagrams",      group: "Technical Manager", keywords: "uml class sequence use case activity state drawio" },
  { label: "Design Document",      to: "sdd",           group: "Technical Manager", keywords: "sdd software design architecture" },
  { label: "Deployment Document",  to: "document",      group: "Technical Manager", keywords: "deploy deployment hosting release plan" },
  { label: "Cost Estimation",      to: "costing",       group: "Technical Manager", keywords: "cost pkr budget price estimate cocomo" },
  { label: "Project Settings",     to: "settings",      group: "General",           keywords: "settings members invite roles activity access" },
  { label: "All Projects",         to: "/boards",       group: "General",           keywords: "projects boards manage new create switch", absolute: true },
];

function filterItems(q) {
  const tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
  if (!tokens.length) return NAV_ITEMS;
  return NAV_ITEMS.map((item) => {
    const label = item.label.toLowerCase();
    const hay = `${label} ${item.group.toLowerCase()} ${item.keywords}`;
    if (!tokens.every((t) => hay.includes(t))) return null;
    const rank = label.startsWith(tokens[0]) ? 0 : label.includes(tokens[0]) ? 1 : 2;
    return { item, rank };
  })
    .filter(Boolean)
    .sort((a, b) => a.rank - b.rank)
    .map((x) => x.item);
}

// ── Search ───────────────────────────────────────────────────────────────────
function SearchBox() {
  const navigate = useNavigate();
  const { boardId } = useActiveBoardId();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrapRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const results = useMemo(() => filterItems(q), [q]);
  const isMac = typeof navigator !== "undefined" && /Mac/i.test(navigator.platform);

  useEffect(() => setActive(0), [q]);

  useEffect(() => {
    const onDown = (e) => {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  useEffect(() => {
    listRef.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const go = (item) => {
    const path = item.absolute ? item.to : boardId ? `/boards/${boardId}/${item.to}` : "/boards";
    navigate(path);
    setQ("");
    setOpen(false);
    inputRef.current?.blur();
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[active]) go(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div ref={wrapRef} className="relative flex-1 min-w-0">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted/70 pointer-events-none">
        <IconSearch />
      </span>
      <input
        ref={inputRef}
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-expanded={open}
        aria-controls="topbar-search-list"
        aria-label="Search tabs and features"
        placeholder="Search tabs & features…"
        className="w-full h-9 pl-9 pr-3 lg:pr-14 rounded-lg bg-surface-2 border border-line text-sm text-ink placeholder:text-ink-muted/60 outline-none focus:border-ink-muted/60 transition"
      />
      <kbd className="hidden lg:block absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-medium text-ink-muted/70 border border-line rounded px-1.5 py-0.5 pointer-events-none">
        {isMac ? "⌘K" : "Ctrl K"}
      </kbd>

      {open && (
        <div className="absolute left-0 right-0 top-full mt-1.5 z-20 bg-surface border border-line rounded-xl shadow-lg overflow-hidden">
          <div ref={listRef} id="topbar-search-list" role="listbox" className="max-h-80 overflow-y-auto py-1">
            {results.length === 0 ? (
              <p className="px-3 py-3 text-sm text-ink-muted/70">No matching tab or feature.</p>
            ) : (
              results.map((item, i) => (
                <button
                  key={item.to}
                  role="option"
                  aria-selected={i === active}
                  onMouseEnter={() => setActive(i)}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => go(item)}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-left text-[13px] transition ${
                    i === active ? "bg-surface-2 text-ink" : "text-ink-muted"
                  }`}
                >
                  <span className="font-medium text-ink">{item.label}</span>
                  {item.soon && (
                    <span className="text-[10px] font-medium text-ink-muted/70 bg-surface-2 border border-line rounded-full px-1.5 py-0.5">
                      Soon
                    </span>
                  )}
                  <span className="ml-auto text-[11px] text-ink-muted/70">{item.group}</span>
                </button>
              ))
            )}
          </div>
          {!boardId && (
            <p className="px-3 py-2 border-t border-line text-[11px] text-ink-muted/70">
              No project selected, tabs will open your project list.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Account menu ─────────────────────────────────────────────────────────────
function readUser() {
  try {
    return JSON.parse(localStorage.getItem("user") || "null");
  } catch {
    return null;
  }
}

function AccountMenu() {
  const navigate = useNavigate();
  const { boardId } = useActiveBoardId();
  const { mode, setMode } = useTheme();
  const user = readUser();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("lastBoardId");
    queryClient.clear(); // don't leak cached data to the next user on this browser
    navigate("/login");
  };

  const name = user?.name || "User";
  const item = "w-full flex items-center gap-2.5 px-3 py-2 text-[13px] text-left transition";

  return (
    <div className="relative ml-auto shrink-0">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2.5 pl-2 pr-1.5 py-1 rounded-lg hover:bg-surface-2 transition"
      >
        <span className="hidden lg:block text-right min-w-0">
          <span className="block text-[13px] font-medium leading-none truncate max-w-[10rem]">{name}</span>
          <span className="block text-[11px] text-ink-muted mt-1 truncate max-w-[10rem]">{user?.email || ""}</span>
        </span>
        <span className="w-8 h-8 rounded-full bg-brand text-brand-fg flex items-center justify-center font-semibold text-sm shrink-0">
          {name.charAt(0).toUpperCase()}
        </span>
        <span className="hidden sm:block text-ink-muted/70"><IconChevron /></span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div role="menu" className="absolute right-0 top-full mt-1.5 z-20 w-64 bg-surface border border-line rounded-xl shadow-lg py-1">
            <div className="px-3 py-2.5 border-b border-line">
              <p className="text-[13px] font-medium truncate">{name}</p>
              <p className="text-xs text-ink-muted truncate">{user?.email || ""}</p>
            </div>

            {/* Theme switch */}
            <div className="px-3 py-2.5">
              <p className="flex items-center gap-2 text-[11px] text-ink-muted mb-1.5">
                <IconPalette /> Theme
              </p>
              <div
                role="radiogroup"
                aria-label="Theme"
                className="grid grid-cols-3 gap-1 p-1 rounded-lg bg-surface-2 border border-line"
              >
                {THEME_OPTIONS.map((o) => (
                  <button
                    key={o.value}
                    role="radio"
                    aria-checked={mode === o.value}
                    onClick={() => setMode(o.value)}
                    className={`flex items-center justify-center gap-1 py-1.5 rounded-md text-[12px] transition ${
                      mode === o.value
                        ? "bg-surface text-ink font-medium shadow-sm"
                        : "text-ink-muted hover:text-ink"
                    }`}
                  >
                    {o.icon}
                    {o.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              role="menuitem"
              onClick={() => { setOpen(false); navigate(boardId ? `/boards/${boardId}/settings` : "/boards"); }}
              className={`${item} text-ink hover:bg-surface-2`}
            >
              <IconSettings /> Settings
            </button>

            <div className="border-t border-line mt-1 pt-1">
              <button role="menuitem" onClick={logout} className={`${item} text-danger hover:bg-danger-soft`}>
                <IconLogout /> Log out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Topbar ───────────────────────────────────────────────────────────────────
// Fixed, full width, h-12 so its bottom border lines up with the sidebar's logo
// row. Left padding follows the sidebar width (expanded or icon-only).
export default function Topbar({ onMenu, assistantOpen, onToggleAssistant }) {
  return (
    <header className="fixed inset-x-0 top-0 z-30 h-12 bg-canvas border-b border-line flex items-center gap-2 px-3 md:pl-[var(--sidebar-w)] md:pr-4 transition-[padding] duration-200 print:hidden">
      {/* Mobile: hamburger + logo (the sidebar is a drawer there) */}
      <div className="flex items-center gap-2 md:hidden shrink-0">
        <button
          onClick={onMenu}
          aria-label="Open menu"
          className="w-9 h-9 flex items-center justify-center rounded-lg text-ink-muted hover:bg-surface-2 transition"
        >
          <IconMenu />
        </button>
        <div className="w-7 h-7 rounded-md bg-brand text-brand-fg flex items-center justify-center font-bold text-sm">S</div>
      </div>

      {/* Centered group */}
      <div className="flex-1 min-w-0 flex items-center gap-2 md:flex-none md:absolute md:left-1/2 md:-translate-x-1/2 md:w-[min(34rem,calc(100vw-34rem))]">
        <SearchBox />
        <button
          onClick={onToggleAssistant}
          aria-pressed={assistantOpen}
          title="Ask AI"
          className={`shrink-0 h-9 inline-flex items-center gap-1.5 rounded-lg px-2.5 lg:px-3 text-[13px] font-medium border transition ${
            assistantOpen
              ? "bg-brand text-brand-fg border-brand"
              : "bg-surface text-ink border-line hover:bg-surface-2"
          }`}
        >
          <IconSparkle />
          <span className="hidden lg:inline">Ask AI</span>
        </button>
      </div>

      <AccountMenu />
    </header>
  );
}