import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("user") || "null");

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b border-neutral-200 bg-white">
<div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
  <div className="flex items-center gap-2 font-semibold tracking-tight">
    <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center font-bold">
      S
    </div>
    StackPilot
  </div>

  <div className="flex items-center gap-4">
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 rounded-full bg-neutral-900 text-white flex items-center justify-center font-semibold">
        {user?.name?.charAt(0) || "U"}
      </div>

      <div>
        <p className="text-sm font-medium">
          {user?.name || "User"}
        </p>

        <p className="text-xs text-neutral-500">
          {user?.email || ""}
        </p>
      </div>
    </div>

    <button
      onClick={logout}
      className="text-sm px-3.5 py-2 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition"
    >
      Sign out
    </button>
  </div>
</div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900">
          Welcome{user?.name ? `, ${user.name}` : ""} 👋
        </h1>
        <p className="mt-2 text-neutral-500">
          You&apos;re signed in. This is your dashboard — start building from
          here.
        </p>

        <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {["Projects", "Deployments", "Team"].map((t) => (
            <div
              key={t}
              className="bg-white border border-neutral-200 rounded-xl p-6 hover:border-neutral-300 transition"
            >
              <p className="text-sm text-neutral-500">{t}</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight">0</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
