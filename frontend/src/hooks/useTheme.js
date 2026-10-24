import { useCallback, useEffect, useRef, useState } from "react";

const KEY = "theme"; // "system" | "light" | "dark"
const query = () => window.matchMedia("(prefers-color-scheme: dark)");

export function getStoredMode() {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(mode, animate = false) {
  const root = document.documentElement;
  const dark = mode === "dark" || (mode === "system" && query().matches);
  const next = dark ? "dark" : "light";
  if (root.getAttribute("data-theme") === next) return;

  if (animate) {
    // Turn colour transitions on just for this switch, then remove them.
    root.classList.add("theme-transition");
    window.clearTimeout(applyTheme._t);
    applyTheme._t = window.setTimeout(
      () => root.classList.remove("theme-transition"),
      350
    );
  }
  root.setAttribute("data-theme", next);
}

export default function useTheme() {
  const [mode, setModeState] = useState(getStoredMode);
  const firstRun = useRef(true);

  useEffect(() => {
    // No animation on first load (the inline script in index.html already set the theme).
    applyTheme(mode, !firstRun.current);
    firstRun.current = false;

    if (mode !== "system") return;
    const mq = query();
    const onChange = () => applyTheme("system", true); // follow the OS live
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [mode]);

  const setMode = useCallback((m) => {
    try { localStorage.setItem(KEY, m); } catch {}
    setModeState(m);
  }, []);

  return { mode, setMode };
}