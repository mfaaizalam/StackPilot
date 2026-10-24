import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";
import AssistantPanel from "./AssistantPanel.jsx";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const isDemoMode = localStorage.getItem("token") === "demo-token";

  return (
    <div className="min-h-screen bg-canvas text-ink md:pl-60 print:pl-0">
      <Sidebar open={mobileOpen} onClose={() => setMobileOpen(false)} />

      <Topbar
        onMenu={() => setMobileOpen(true)}
        assistantOpen={assistantOpen}
        onToggleAssistant={() => setAssistantOpen((v) => !v)}
      />

      {/* Lives here (not in a page) so the conversation survives navigation */}
      <AssistantPanel open={assistantOpen} onClose={() => setAssistantOpen(false)} />

      {/* pt-12 = topbar height. Dotted canvas lives here, so every routed page gets it */}
      <main className="app-dotted min-w-0 pt-12 print:pt-0">
        {isDemoMode && (
          <div className="bg-warning-soft text-warning text-xs text-center py-1.5">
            Demo mode: read-only sample data. Backend offline.
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}