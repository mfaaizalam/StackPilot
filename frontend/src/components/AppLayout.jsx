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

  return (
    <div className="min-h-screen bg-neutral-50 md:pl-60 print:pl-0">
      <Sidebar open={mobileOpen} onClose={() => setMobileOpen(false)} />

      {/* Mobile top bar (the sidebar is a slide-in drawer below md) */}
      <div className="md:hidden h-14 px-3 flex items-center gap-3 bg-white border-b border-neutral-200 print:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
          className="w-9 h-9 flex items-center justify-center rounded-lg text-neutral-600 hover:bg-neutral-100 transition"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M3 5h12M3 9h12M3 13h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>
        <div className="flex items-center gap-2 font-semibold tracking-tight">
          <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center font-bold text-sm">
            S
          </div>
          StackPilot
        </div>
      </div>

      <main className="min-w-0">
        <Outlet />
      </main>
    </div>
  );
}