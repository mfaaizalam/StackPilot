import { useEffect, useState } from "react";

/* ───────── mermaid is large: load it only when a diagram is first shown ───────── */
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
        htmlLabels: false, // pure SVG text => PNG export works (no foreignObject)
        flowchart: { htmlLabels: false, curve: "basis", padding: 12 },
        class: { htmlLabels: false },
        sequence: { useMaxWidth: true, mirrorActors: false, showSequenceNumbers: false },
        state: { useMaxWidth: true },
      });
      return mermaid;
    });
  }
  return mermaidPromise;
}

let counter = 0;

/* ───────── export helpers ───────── */
function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Give the <svg> explicit pixel size (from its viewBox) so it can be drawn on a canvas. */
function sizedSvg(svgText) {
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const el = doc.documentElement;
  const vb = (el.getAttribute("viewBox") || "").split(/[\s,]+/).map(Number);
  let w = vb[2], h = vb[3];
  if (!w || !h) { w = parseFloat(el.getAttribute("width")) || 800; h = parseFloat(el.getAttribute("height")) || 600; }
  el.setAttribute("width", w); el.setAttribute("height", h);
  el.removeAttribute("style");
  if (!el.getAttribute("xmlns")) el.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  return { text: new XMLSerializer().serializeToString(el), w, h };
}

function svgToPng(svgText, filename) {
  const { text, w, h } = sizedSvg(svgText);
  const img = new Image();
  img.onload = () => {
    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = w * scale; canvas.height = h * scale;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((b) => b && download(b, filename), "image/png");
  };
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(text);
}

const safeName = (s) => (s || "diagram").replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "").slice(0, 50) || "diagram";

/* ───────── the card ───────── */
export default function DiagramCard({ d }) {
  const [svg, setSvg] = useState(d.svg || "");
  const [failed, setFailed] = useState(!!d.error);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let alive = true;
    if (d.svg) { setSvg(d.svg); setFailed(false); return; }
    if (!d.mermaid) return;
    setFailed(false);
    loadMermaid()
      .then((mermaid) => mermaid.render(`dg-${d.id}-${++counter}`, d.mermaid))
      .then(({ svg: out }) => { if (alive) setSvg(out); })
      .catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, [d.id, d.svg, d.mermaid]);

  const name = safeName(d.title);
  const canvasCls = "[&_svg]:max-w-full [&_svg]:h-auto [&_svg]:mx-auto";

  return (
    <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden print:break-inside-avoid">
      <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 border-b border-neutral-100">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="text-sm font-semibold text-neutral-900 truncate">{d.title}</h3>
          {d.stale && <span className="text-[10px] font-medium bg-amber-100 text-amber-800 rounded-full px-2 py-0.5">Out of date</span>}
          {d.source === "fallback" && <span className="text-[10px] font-medium bg-neutral-100 text-neutral-600 rounded-full px-2 py-0.5">Drawn from requirements</span>}
        </div>
        <div className="flex items-center gap-1.5 print:hidden">
          <button disabled={!svg} onClick={() => setExpanded(true)} className="text-xs px-2.5 py-1 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition disabled:opacity-40">Expand</button>
          <button disabled={!svg} onClick={() => download(new Blob([sizedSvg(svg).text], { type: "image/svg+xml" }), `${name}.svg`)} className="text-xs px-2.5 py-1 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition disabled:opacity-40">SVG</button>
          <button disabled={!svg} onClick={() => svgToPng(svg, `${name}.png`)} className="text-xs px-2.5 py-1 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition disabled:opacity-40">PNG</button>
          {d.mermaid && <button onClick={() => download(new Blob([d.mermaid], { type: "text/plain" }), `${name}.mmd`)} className="text-xs px-2.5 py-1 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">Mermaid</button>}
        </div>
      </div>

      <div className="p-5 overflow-x-auto">
        {failed ? (
          <div className="text-sm text-neutral-600">
            <p className="mb-2">This diagram could not be drawn in your browser.</p>
            {d.mermaid && <details><summary className="cursor-pointer text-xs text-neutral-500">Show diagram source</summary><pre className="mt-2 text-xs bg-neutral-50 border border-neutral-200 rounded-lg p-3 overflow-x-auto">{d.mermaid}</pre></details>}
          </div>
        ) : svg ? (
          <div className={canvasCls} dangerouslySetInnerHTML={{ __html: svg }} />
        ) : (
          <div className="h-40 rounded-xl bg-neutral-50 animate-pulse" />
        )}
      </div>

      {d.warnings?.length > 0 && (
        <ul className="px-5 pb-4 -mt-1 space-y-1 print:hidden">
          {d.warnings.map((w, i) => <li key={i} className="text-xs text-amber-700">• {w}</li>)}
        </ul>
      )}

      {expanded && (
        <div className="fixed inset-0 z-50 bg-white overflow-auto print:hidden" onClick={() => setExpanded(false)}>
          <div className="sticky top-0 flex items-center justify-between bg-white/95 backdrop-blur border-b border-neutral-200 px-6 h-14">
            <span className="text-sm font-semibold text-neutral-900">{d.title}</span>
            <button className="text-sm px-3 py-1.5 rounded-lg border border-neutral-200 hover:bg-neutral-100">Close</button>
          </div>
          <div className="p-6 [&_svg]:w-full [&_svg]:h-auto [&_svg]:min-w-[760px] [&_svg]:max-w-none" onClick={(e) => e.stopPropagation()} dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
      )}
    </div>
  );
}
