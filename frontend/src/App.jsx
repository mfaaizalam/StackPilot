import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Boards from "./pages/Boards.jsx";
import BoardDetail from "./pages/BoardDetail.jsx";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
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
    </Routes>
  );
}