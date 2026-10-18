import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "../api/axios.js";

const errText = (e, fallback) => e?.response?.data?.detail || fallback;

export default function InviteAccept() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["invite-preview", token],
    queryFn: () => api.get(`/invitations/token/${token}`).then((r) => r.data),
    retry: false,
  });

  useEffect(() => {
    if (loadError) setError(errText(loadError, "Could not open this invitation."));
  }, [loadError]);

  const accept = async () => {
    setBusy(true);
    setError("");
    try {
      const { data: res } = await api.post(`/invitations/token/${token}/accept`);
      localStorage.setItem("lastBoardId", String(res.board_id));
      navigate(`/boards/${res.board_id}/kanban`, { replace: true });
    } catch (e) {
      setError(errText(e, "Could not accept the invitation."));
      setBusy(false);
    }
  };

  const switchAccount = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate(`/login?next=${encodeURIComponent(`/invite/${token}`)}`, { replace: true });
  };

  return (
    <div className="max-w-md mx-auto mt-16 bg-white border border-neutral-200 rounded-2xl p-8">
      <h1 className="text-xl font-semibold text-neutral-900">Project invitation</h1>

      {isLoading && <p className="mt-4 text-sm text-neutral-500">Loading invitation…</p>}

      {data && !error && (
        <>
          <p className="mt-4 text-sm text-neutral-700">
            You have been invited to join <b>{data.board_name}</b> as{" "}
            <b>{data.role.replace("_", " ")}</b>.
          </p>
          <button
            onClick={accept}
            disabled={busy}
            className="mt-6 w-full bg-neutral-900 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-neutral-800 disabled:opacity-60"
          >
            {busy ? "Joining…" : "Accept invitation"}
          </button>
        </>
      )}

      {error && (
        <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {error && (
        <div className="mt-4 flex gap-4 text-sm">
          <button onClick={switchAccount} className="font-medium text-neutral-900 hover:underline">
            Sign in with a different account
          </button>
          <Link to="/boards" className="text-neutral-500 hover:underline">Go to my boards</Link>
        </div>
      )}
    </div>
  );
}