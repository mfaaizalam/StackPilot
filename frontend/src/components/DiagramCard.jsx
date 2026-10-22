import { useEffect, useState } from "react";
import api from "../api/axios.js";
import DrawioEditor from "./DrawioEditor.jsx";

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
export default function DiagramCard({ d, boardId, onChanged }) {
  const [svg, setSvg] = useState(d.svg || "");
  const [failed, setFailed] = useState(!!d.error);
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const canEdit = !!(boardId && d.id);
  const reset = async () => {
    if (!window.confirm("Discard your changes and go back to the generated diagram?")) return;
    try { await api.delete(`/boards/${boardId}/srs/diagrams/${d.id}/drawio`); onChanged?.(); } catch { /* keep the card usable */ }
  };

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
  // Native draw.io file: every shape (UML, ER, DFD ...) stays editable with the full draw.io shape library
  const drawio = async () => {
    try {
      const { data } = await api.get(`/boards/${boardId}/srs/diagrams/${d.id}/export.drawio`, { responseType: "blob" });
      download(data, `${name}.drawio`);
    } catch { /* the toolbar stays usable; the file simply is not downloaded */ }
  };
  // Diagrams are drawn for a light background (Mermaid "neutral" theme + the
  // code-built use-case SVG), and PNG export is white, so the image always sits on
  // a white "paper" panel regardless of the site theme. bg-white is intentional.
  const canvasCls = "bg-white rounded-lg p-3 [&_svg]:max-w-full [&_svg]:h-auto [&_svg]:mx-auto";
  const btn = "text-xs px-2.5 py-1 rounded-lg border border-line text-ink hover:bg-surface-2 transition disabled:opacity-40";

  return (
    <div className="bg-surface border border-line rounded-card overflow-hidden print:break-inside-avoid">
      <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 border-b border-line">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="text-sm font-semibold text-ink truncate">{d.title}</h3>
          {d.edited && <span className="text-[10px] font-medium bg-surface-2 text-ink-muted rounded-full px-2 py-0.5">Edited by you</span>}
          {d.stale && <span className="text-[10px] font-medium bg-warning-soft text-warning rounded-full px-2 py-0.5">Out of date</span>}
          {d.source === "fallback" && <span className="text-[10px] font-medium bg-surface-2 text-ink-muted rounded-full px-2 py-0.5">Drawn from requirements</span>}
        </div>
        <div className="flex items-center gap-1.5 print:hidden">
          {canEdit && <button onClick={() => setEditing(true)} className="text-xs px-2.5 py-1 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition">Edit</button>}
          {d.edited && <button onClick={reset} className={btn}>Reset</button>}
          <button disabled={!svg && !d.edited_png} onClick={() => setExpanded(true)} className={btn}>Expand</button>
          <button disabled={!svg || d.edited} onClick={() => download(new Blob([sizedSvg(svg).text], { type: "image/svg+xml" }), `${name}.svg`)} className={btn}>SVG</button>
          <button disabled={!svg && !d.edited_png} onClick={() => d.edited_png ? fetch(d.edited_png).then((r) => r.blob()).then((b) => download(b, `${name}.png`)) : svgToPng(svg, `${name}.png`)} className={btn}>PNG</button>
          {boardId && d.id && <button onClick={drawio} title="Download an editable draw.io file" className={btn}>draw.io</button>}
          {d.mermaid && <button onClick={() => download(new Blob([d.mermaid], { type: "text/plain" }), `${name}.mmd`)} className={btn}>Mermaid</button>}
        </div>
      </div>

      <div className="p-5 overflow-x-auto">
        {failed ? (
          <div className="text-sm text-ink-muted">
            <p className="mb-2">This diagram could not be drawn in your browser.</p>
            {d.mermaid && <details><summary className="cursor-pointer text-xs text-ink-muted">Show diagram source</summary><pre className="mt-2 text-xs text-ink bg-surface-2 border border-line rounded-lg p-3 overflow-x-auto">{d.mermaid}</pre></details>}
          </div>
        ) : d.edited_png ? (
          <div className={canvasCls}><img src={d.edited_png} alt={d.title} /></div>
        ) : svg ? (
          <div className={canvasCls} dangerouslySetInnerHTML={{ __html: svg }} />
        ) : (
          <div className="h-40 rounded-card bg-surface-2 animate-pulse" />
        )}
      </div>

      {d.warnings?.length > 0 && (
        <ul className="px-5 pb-4 -mt-1 space-y-1 print:hidden">
          {d.warnings.map((w, i) => <li key={i} className="text-xs text-warning">• {w}</li>)}
        </ul>
      )}

      {editing && <DrawioEditor boardId={boardId} diagram={d} onClose={() => setEditing(false)} onSaved={onChanged} />}

      {expanded && (
        <div className="fixed inset-0 z-50 bg-canvas text-ink overflow-auto print:hidden" onClick={() => setExpanded(false)}>
          <div className="sticky top-0 flex items-center justify-between bg-surface/95 backdrop-blur border-b border-line px-6 h-14">
            <span className="text-sm font-semibold text-ink">{d.title}</span>
            <button className="text-sm px-3 py-1.5 rounded-lg border border-line hover:bg-surface-2">Close</button>
          </div>
          <div className="p-6">
            <div className="bg-white rounded-card p-6 [&_svg]:w-full [&_svg]:h-auto [&_svg]:min-w-[760px] [&_svg]:max-w-none" onClick={(e) => e.stopPropagation()} dangerouslySetInnerHTML={{ __html: d.edited_png ? `<img src="${d.edited_png}" alt="" />` : svg }} />
          </div>
        </div>
      )}
    </div>
  );
}