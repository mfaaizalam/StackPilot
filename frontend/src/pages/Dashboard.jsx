import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios.js";

function IconBoards() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="2" y="2" width="7" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="11" y="2" width="7" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="11" y="10" width="7" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="2" y="14" width="7" height="4" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  );
}
function IconColumns() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="2" y="3" width="4" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="8" y="3" width="4" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="14" y="3" width="4" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  );
}
function IconTasks() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M7 10l2.5 2.5L14 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <rect x="2" y="2" width="16" height="16" rx="3" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  );
}
function IconArrow() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3 7h8M7.5 4l3.5 3-3.5 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("user") || "null");

  const [stats, setStats] = useState({ boards: null, columns: null, tasks: null });
  const [recentBoards, setRecentBoards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [boardsRes, colsRes, tasksRes] = await Promise.all([
          api.get("/boards/"),
          api.get("/columns/"),
          api.get("/tasks/"),
        ]);
        setStats({
          boards: boardsRes.data.length,
          columns: colsRes.data.length,
          tasks: tasksRes.data.length,
        });
        setRecentBoards(boardsRes.data.slice(-4).reverse());
      } catch {
        setStats({ boards: "—", columns: "—", tasks: "—" });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  const STAT_CARDS = [
    { label: "Boards", key: "boards",  icon: <IconBoards />,  route: "/boards" },
    { label: "Columns", key: "columns", icon: <IconColumns />, route: null },
    { label: "Tasks",   key: "tasks",   icon: <IconTasks />,   route: null },
  ];

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="border-b border-neutral-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 font-semibold tracking-tight">
              <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center font-bold text-sm">S</div>
              StackPilot
            </div>
            <nav className="hidden sm:flex items-center gap-1">
              <button className="text-sm px-3 py-1.5 rounded-md bg-neutral-100 text-neutral-900 font-medium">Home</button>
              <button onClick={() => navigate("/boards")} className="text-sm px-3 py-1.5 rounded-md text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 transition">Boards</button>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-neutral-900 text-white flex items-center justify-center font-semibold text-sm">
              {user?.name?.charAt(0) || "U"}
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-medium leading-none">{user?.name || "User"}</p>
              <p className="text-xs text-neutral-500 mt-0.5">{user?.email || ""}</p>
            </div>
            <button onClick={logout} className="text-sm px-3.5 py-2 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Greeting */}
        <div className="flex items-start justify-between flex-wrap gap-4 mb-10">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
              Welcome back{user?.name ? `, ${user.name}` : ""} 👋
            </h1>
            <p className="mt-1 text-sm text-neutral-500">Here's what's happening across your workspace.</p>
          </div>
          <button
            onClick={() => navigate("/boards")}
            className="flex items-center gap-2 bg-neutral-950 text-white text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-neutral-800 transition"
          >
            Go to Boards <IconArrow />
          </button>
        </div>

        {/* Stat cards */}
        <div className="grid sm:grid-cols-3 gap-4 mb-10">
          {STAT_CARDS.map(({ label, key, icon, route }) => (
            <div
              key={key}
              onClick={() => route && navigate(route)}
              className={`bg-white border border-neutral-200 rounded-xl p-6 flex items-center gap-4 hover:border-neutral-300 transition ${route ? "cursor-pointer" : ""}`}
            >
              <div className="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center text-neutral-600 shrink-0">
                {icon}
              </div>
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wide font-medium">{label}</p>
                <p className="mt-0.5 text-2xl font-semibold tracking-tight text-neutral-900">
                  {loading ? <span className="inline-block w-8 h-6 bg-neutral-100 rounded animate-pulse" /> : stats[key]}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Recent boards */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-neutral-900">Recent boards</h2>
            <button onClick={() => navigate("/boards")} className="text-xs text-neutral-500 hover:text-neutral-900 underline underline-offset-2 transition flex items-center gap-1">
              View all <IconArrow />
            </button>
          </div>

          {loading && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[1,2,3,4].map(i => <div key={i} className="h-24 bg-white border border-neutral-200 rounded-xl animate-pulse" />)}
            </div>
          )}

          {!loading && recentBoards.length === 0 && (
            <div className="py-12 text-center border border-dashed border-neutral-200 rounded-xl">
              <p className="text-sm text-neutral-500">No boards yet.</p>
              <button onClick={() => navigate("/boards")} className="mt-3 text-sm text-neutral-900 font-medium underline underline-offset-2">Create your first board</button>
            </div>
          )}

          {!loading && recentBoards.length > 0 && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {recentBoards.map((b) => {
                const initials = b.name.split(" ").slice(0, 2).map(w => w[0]?.toUpperCase() || "").join("");
                return (
                  <div
                    key={b.id}
                    onClick={() => navigate(`/boards/${b.id}`)}
                    className="bg-white border border-neutral-200 rounded-xl p-4 hover:border-neutral-300 hover:shadow-sm transition cursor-pointer flex flex-col gap-3"
                  >
                    <div className="w-8 h-8 rounded-md bg-neutral-950 text-white flex items-center justify-center text-xs font-semibold">{initials || "B"}</div>
                    <div>
                      <p className="text-sm font-medium text-neutral-900 truncate">{b.name}</p>
                      {b.description && <p className="text-xs text-neutral-500 mt-0.5 truncate">{b.description}</p>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}