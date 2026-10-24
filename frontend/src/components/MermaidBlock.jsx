import { useEffect, useState } from "react";

/* Mermaid is large: load it only when the first diagram is shown (same approach as DiagramCard). */
let mermaidPromise = null;
function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import("mermaid").then((m) => {
      const mermaid = m.default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "neutral",
        securityLevel: "strict",
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        htmlLabels: false,
        flowchart: { htmlLabels: false, curve: "basis", padding: 12 },
        class: { htmlLabels: false },
        sequence: { useMaxWidth: true, mirrorActors: false },
        state: { useMaxWidth: true },
      });
      return mermaid;
    });
  }
  return mermaidPromise;
}

let counter = 0;

// Renders one ```mermaid block found inside the SDD markdown.
// If the diagram cannot be drawn, the source is shown instead so nothing is lost.
export default function MermaidBlock({ source }) {
  const [svg, setSvg] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    setSvg(""); setFailed(false);
    loadMermaid()
      .then((mermaid) => mermaid.render(`sdd-mm-${++counter}`, source))
      .then(({ svg: out }) => { if (alive) setSvg(out); })
      .catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, [source]);

  if (failed) {
    return (
      <div className="mb-4">
        <p className="text-xs text-warning bg-warning-soft border border-warning/30 rounded-lg px-3 py-2 mb-2">
          This diagram could not be drawn. Its source is shown below.
        </p>
        <pre className="text-xs bg-surface-2 border border-line rounded-lg p-3 overflow-x-auto">{source}</pre>
      </div>
    );
  }
  if (!svg) return <div className="h-32 mb-4 bg-surface-2 border border-line rounded-xl animate-pulse" />;

  return (
    <div
      className="mb-5 bg-white border border-line rounded-xl p-4 overflow-x-auto print:break-inside-avoid [&_svg]:max-w-full [&_svg]:h-auto [&_svg]:mx-auto"
      role="img"
      aria-label="Diagram"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}