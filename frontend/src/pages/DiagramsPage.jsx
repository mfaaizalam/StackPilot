import { useParams } from "react-router-dom";
import SrsGate from "../components/SrsGate.jsx";
import DiagramsPanel from "../components/DiagramsPanel.jsx";

export default function DiagramsPage() {
  const { boardId } = useParams();
  return (
    <SrsGate title="Diagrams">
      {(doc) => (
        <DiagramsPanel boardId={boardId} srsId={doc.id} version={doc.version} />
      )}
    </SrsGate>
  );
}