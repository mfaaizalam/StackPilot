import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api/axios.js";

/* Full draw.io editor inside the app (embed mode). The diagram opens with every shape editable and the whole
   shape library available (UML, ER, flowchart, BPMN, network, cloud icons, mockups ...). "Save" stores the
   diagram and a picture of it in the database; the Word exports use that picture. */
const EMBED = "https://embed.diagrams.net/?embed=1&proto=json&spin=1&saveAndExit=1&noExitBtn=0&lang=en"
  + "&libs=general;uml;er;flowchart;basic;arrows2;bpmn;network;aws4;azure;gcp2;kubernetes;mockups;cisco;android;ios";

export default function DrawioEditor({ boardId, diagram, onClose, onSaved }) {
  const frame = useRef(null);
  const pending = useRef({ xml: null, exit: false });
  const closeAfter = useRef(false);
  const saving = useRef(false);
  const [status, setStatus] = useState("Loading the editor…");
  const [error, setError] = useState("");

  const post = useCallback((msg) => frame.current?.contentWindow?.postMessage(JSON.stringify(msg), "*"), []);

  const persist = useCallback(async (xml, png) => {
    try {
      await api.put(`/boards/${boardId}/srs/diagrams/${diagram.id}/drawio`, { xml, png });
      post({ action: "status", message: "Saved", modified: false });
      setStatus("Saved"); onSaved?.();
      if (pending.current.exit || closeAfter.current) onClose();
    } catch (e) {
      const d = e?.response?.data?.detail;
      setError(typeof d === "string" ? d : "Could not save the diagram. Please try again.");
    } finally { saving.current = false; }
  }, [boardId, diagram.id, onClose, onSaved, post]);

  useEffect(() => {
    let alive = true;
    const onMsg = async (ev) => {
      if (ev.source !== frame.current?.contentWindow || typeof ev.data !== "string") return;
      let m; try { m = JSON.parse(ev.data); } catch { return; }
      if (m.event === "init") {
        try {
          const { data } = await api.get(`/boards/${boardId}/srs/diagrams/${diagram.id}/drawio`);
          if (alive) { post({ action: "load", autosave: 0, xml: data.xml, title: diagram.title }); setStatus(""); }
        } catch { setError("Could not load the diagram."); }
      } else if (m.event === "save") {
        saving.current = true; pending.current = { xml: m.xml, exit: !!m.exit }; setStatus("Saving…");
        post({ action: "export", format: "png", xml: m.xml, scale: 2, spin: "Saving" });
      } else if (m.event === "export") {
        persist(pending.current.xml, m.data);
      } else if (m.event === "exit") {
        if (saving.current) closeAfter.current = true; else onClose();
      }
    };
    window.addEventListener("message", onMsg);
    return () => { alive = false; window.removeEventListener("message", onMsg); };
  }, [boardId, diagram.id, diagram.title, onClose, persist, post]);

  return (
    <div className="fixed inset-0 z-[60] bg-canvas flex flex-col print:hidden">
      <div className="flex items-center justify-between px-5 h-12 border-b border-line bg-surface shrink-0">
        <span className="text-sm font-semibold text-ink truncate">Editing: {diagram.title}</span>
        <div className="flex items-center gap-3">
          <span className="text-xs text-ink-muted">{status}</span>
          <button onClick={onClose} className="text-xs px-3 py-1.5 rounded-lg border border-line hover:bg-surface-2">Close</button>
        </div>
      </div>
      {error && <p className="text-sm text-danger bg-danger-soft px-5 py-2">{error}</p>}
      <iframe ref={frame} title="Diagram editor" src={EMBED} className="flex-1 w-full border-0 bg-white" />
    </div>
  );
}
