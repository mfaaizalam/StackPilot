import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar.jsx";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const isDemoMode = localStorage.getItem("token") === "demo-token";

  return (
    <div className="min-h-screen bg-canvas text-ink md:pl-60 print:pl-0">
      {/* Demo mode banner */}
      {isDemoMode && (
        <div className="bg-warning-soft text-warning text-xs text-center py-1.5">
          Demo mode: read-only sample data. Backend offline.
        </div>
      )}

      <Sidebar
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
      />

      {/* Mobile top bar */}
      <div className="md:hidden h-14 px-3 flex items-center gap-3 bg-surface border-b border-line print:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
          className="w-9 h-9 flex items-center justify-center rounded-lg text-ink-muted hover:bg-surface-2 transition"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M3 5h12M3 9h12M3 13h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>

        <div className="flex items-center gap-2 font-semibold tracking-tight">
          <div className="w-7 h-7 rounded-md bg-brand text-brand-fg flex items-center justify-center font-bold text-sm">
            S
          </div>
          StackPilot
        </div>
      </div>

      {/* Dotted canvas lives here, so every routed page gets it */}
      <main className="app-dotted min-w-0">
        <Outlet />
      </main>
    </div>
  );
}