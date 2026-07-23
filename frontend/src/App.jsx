import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Boards from "./pages/Boards.jsx";
import BoardDetail from "./pages/BoardDetail.jsx";
import ProjectAnalysis from "./pages/ProjectAnalysis.jsx";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
      <Route
        path="/boards"
        element={
          <PrivateRoute>
            <Boards />
          </PrivateRoute>
        }
      />
      <Route
        path="/boards/:boardId"
        element={
          <PrivateRoute>
            <BoardDetail />
          </PrivateRoute>
        }
      />
      <Route
        path="/boards/:boardId/analyze"
        element={
          <PrivateRoute>
            <ProjectAnalysis />
          </PrivateRoute>
        }
      />
    </Routes>
  );
}