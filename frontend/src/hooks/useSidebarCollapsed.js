import { useEffect, useState } from "react";

const KEY = "sidebarMenuCollapsed";

export default function useSidebarCollapsed() {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
  });

  useEffect(() => {
    document.documentElement.dataset.sidebar = collapsed ? "collapsed" : "expanded";
    try { localStorage.setItem(KEY, collapsed ? "1" : "0"); } catch {}
  }, [collapsed]);

  return [collapsed, setCollapsed];
}