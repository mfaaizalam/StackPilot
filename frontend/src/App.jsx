import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Boards from "./pages/Boards.jsx";
import BoardDetail from "./pages/BoardDetail.jsx";
import SrsStudio from "./pages/SrsStudio.jsx";
import DiagramsPage from "./pages/DiagramsPage.jsx";
import CostingPage from "./pages/CostingPage.jsx";
import ComingSoonPage from "./pages/ComingSoonPage.jsx";
import NotFound from "./pages/NotFound.jsx";
import AppLayout from "./components/AppLayout.jsx";
import { useBoards } from "./api/queries.js";
import SddPage from "./pages/SddPage.jsx";

// Auth gate + sidebar layout for every logged-in page.
function PrivateLayout() {
  const token = localStorage.getItem("token");
  return token ? <AppLayout /> : <Navigate to="/login" replace />;
}

// "/dashboard" is kept as the post-login landing target (Login.jsx can keep
// navigating there). It sends the user to their last-used project's Kanban
// board, or to the project list if they have none yet.
function HomeRedirect() {
  const { data: boards, isLoading, isError } = useBoards();

  if (isLoading) {
    return <div className="p-10 text-sm text-neutral-500">Loading…</div>;
  }
  if (isError || !boards?.length) {
    return <Navigate to="/boards" replace />;
  }

  const lastId = localStorage.getItem("lastBoardId");
  const target =
    boards.find((b) => String(b.id) === lastId) ||
    [...boards].sort((a, b) => b.id - a.id)[0];

  return <Navigate to={`/boards/${target.id}/kanban`} replace />;
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Logged-in pages share the sidebar layout */}
      <Route element={<PrivateLayout />}>
        <Route path="/dashboard" element={<HomeRedirect />} />
        <Route path="/boards" element={<Boards />} />

        {/* Old bare board URL -> Kanban */}
        <Route path="/boards/:boardId" element={<Navigate to="kanban" replace />} />
        <Route path="/boards/:boardId/kanban" element={<BoardDetail />} />
        <Route path="/boards/:boardId/srs" element={<SrsStudio />} />
        <Route path="/boards/:boardId/sdd" element={<SddPage />} />
        <Route path="/boards/:boardId/diagrams" element={<DiagramsPage />} />
        <Route path="/boards/:boardId/costing" element={<CostingPage />} />

        {/* Not built yet */}
        <Route path="/boards/:boardId/sdd" element={<ComingSoonPage title="SDD" description="Software Design Document generation is on its way." />} />
        <Route path="/boards/:boardId/settings" element={<ComingSoonPage title="Settings" description="Project settings are on their way." />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}