import { useParams } from "react-router-dom";
import SrsGate from "../components/SrsGate.jsx";
import CostPanel from "../components/CostPanel.jsx";

export default function CostingPage() {
  const { boardId } = useParams();
  return (
    <SrsGate title="Costing">
      {(doc) => (
        <CostPanel key={doc.id} boardId={boardId} srsId={doc.id} version={doc.version} />
      )}
    </SrsGate>
  );
}