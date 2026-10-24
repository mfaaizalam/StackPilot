import { useEffect, useState } from "react";
import { Outlet, useLocation, useMatch } from "react-router-dom";
import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";
import AssistantPanel from "./AssistantPanel.jsx";
import { useBoards } from "../api/queries.js";
import useDocumentTitle from "../hooks/useDocumentTitle.js";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const location = useLocation();

  // Browser tab title: "<Page> · <Project> | StackPilot"
  const { data: boards = [] } = useBoards();
  const match = useMatch("/boards/:boardId/*");
  const boardName = boards.find(
    (b) => String(b.id) === String(match?.params?.boardId)
  )?.name;
  useDocumentTitle(boardName, "app");

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);
  

  return (
    <div className="min-h-screen bg-canvas text-ink md:pl-[var(--sidebar-w)] transition-[padding] duration-200 print:pl-0">
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
        <Outlet />
      </main>
    </div>
  );
}