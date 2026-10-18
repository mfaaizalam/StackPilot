import { useParams } from "react-router-dom";
import SrsGate from "../components/SrsGate.jsx";
import SddPanel from "../components/SddPanel.jsx";

// Same shape as CostingPage: SrsGate loads the latest SRS, the panel does the work.
export default function SddPage() {
  const { boardId } = useParams();
  return (
    <SrsGate title="Design Document">
      {(doc) => (
        <SddPanel key={doc.id} boardId={boardId} srsId={doc.id} version={doc.version} />
      )}
    </SrsGate>
  );
}