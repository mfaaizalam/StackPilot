
import { Routes, Route, Navigate, Outlet } from "react-router-dom";

import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Boards from "./pages/Boards.jsx";
import BoardDetail from "./pages/BoardDetail.jsx";
import SrsStudio from "./pages/SrsStudio.jsx";
import DiagramsPage from "./pages/DiagramsPage.jsx";
import CostingPage from "./pages/CostingPage.jsx";
import BoardSettings from "./pages/BoardSettings.jsx";
import AcceptInvite from "./pages/AcceptInvite.jsx";
import ComingSoonPage from "./pages/ComingSoonPage.jsx";
import NotFound from "./pages/NotFound.jsx";
import AppLayout from "./components/AppLayout.jsx";
import { useBoards } from "./api/queries.js";
import SddPage from "./pages/SddPage.jsx";
import GanttPage from "./pages/GanttPage.jsx";

function PrivateLayout() {
  const token = localStorage.getItem("token");

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}

function HomeRedirect() {
  const { data: boards, isLoading, isError } = useBoards();

  if (isLoading) {
    return (
      <div className="p-10 text-sm text-neutral-500">
        Loading…
      </div>
    );
  }

  if (isError || !boards?.length) {
    return <Navigate to="/boards" replace />;
  }

  const lastId = localStorage.getItem("lastBoardId");

  const target =
    boards.find((board) => String(board.id) === lastId) ||
    [...boards].sort((a, b) => b.id - a.id)[0];

  return (
    <Navigate
      to={`/boards/${target.id}/kanban`}
      replace
    />
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      {/* Public on purpose: the email link must work before login. Accepting needs a login. */}
      <Route path="/invite/:token" element={<AcceptInvite />} />

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
        <Route path="/boards/:boardId/timeline" element={<GanttPage />} />

        <Route
          path="/boards/:boardId/kanban"
          element={<BoardDetail />}
        />

        <Route
          path="/boards/:boardId/srs"
          element={<SrsStudio />}
        />

        <Route
          path="/boards/:boardId/diagrams"
          element={<DiagramsPage />}
        />

        <Route
          path="/boards/:boardId/costing"
          element={<CostingPage />}
        />

        <Route
          path="/boards/:boardId/settings"
          element={<BoardSettings />}
        />

        <Route
          path="/boards/:boardId/sdd"
          element={
            <ComingSoonPage
              title="SDD"
              description="Software Design Document generation is on its way."
            />
          }
        />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
