import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const SECTION_TITLES = {
  overview: "Overview",
  kanban: "Kanban Board",
  timeline: "Gantt Chart",
  "github-issues": "GitHub Issues",
  scope: "Project Scope",
  srs: "SRS Document",
  diagrams: "Diagrams",
  sdd: "Design Document",
  document: "Deployment Document",
  costing: "Cost Estimation",
  settings: "Project Settings",
};

const PUBLIC_TITLES = {
  "/": null, // landing page: just "StackPilot"
  "/login": "Log in",
  "/register": "Sign up",
};

/**
 * scope "public": handles pages outside the app layout (mounted in App.jsx)
 * scope "app":    handles /boards/* and /dashboard (mounted in AppLayout)
 * Each instance ignores the other's routes, so they never overwrite each other.
 */
export default function useDocumentTitle(boardName, scope = "public") {
  const { pathname } = useLocation();

  useEffect(() => {
    const parts = pathname.split("/").filter(Boolean);
    const isAppRoute = parts[0] === "boards" || pathname === "/dashboard";
    if (isAppRoute !== (scope === "app")) return;

    let page;
    if (parts[0] === "boards" && parts[1]) {
      page = SECTION_TITLES[parts[2]] || "Project";
      if (boardName) page = `${page} · ${boardName}`;
    } else if (parts[0] === "boards") {
      page = "All Projects";
    } else if (pathname === "/dashboard") {
      page = "Dashboard";
    } else if (parts[0] === "invite") {
      page = "Accept invitation";
    } else if (pathname in PUBLIC_TITLES) {
      page = PUBLIC_TITLES[pathname];
    } else {
      page = "Page not found";
    }

    document.title = page ? `${page} | StackPilot` : "StackPilot";
  }, [pathname, boardName, scope]);
}