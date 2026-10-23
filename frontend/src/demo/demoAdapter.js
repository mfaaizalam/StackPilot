import axios from "axios";
import data from "./demoAccount.json";

const ok = (config, body) =>
  Promise.resolve({ data: body, status: 200, statusText: "OK", headers: {}, config, request: {} });

const fail = (config, status, detail) =>
  Promise.reject(
    new axios.AxiosError(detail, "ERR_BAD_REQUEST", config, {}, {
      data: { detail }, status, statusText: detail, headers: {}, config,
    })
  );

const bid = (s) => Number(s);
const srsDocs = (boardId) =>
  data.srs_documents.filter((d) => d.board_id === bid(boardId)).sort((a, b) => b.version - a.version);
const sddDocs = (boardId) =>
  data.sdd_documents.filter((d) => d.board_id === bid(boardId)).sort((a, b) => b.version - a.version);
const pick = (docs, version) => (version ? docs.find((d) => d.version === Number(version)) : docs[0]);

// [regex, handler(match, config)] -- handler returns body, Blob, or undefined (= 404)
const ROUTES = [
  [/^\/boards$/, () => data.boards],
  [/^\/columns$/, () => data.columns],
  [/^\/tasks$/, () => data.tasks],
  [/^\/boards\/(\d+)$/, (m) => data.boards.find((b) => b.id === bid(m[1]))],
  [/^\/boards\/(\d+)\/me$/, (m) => ({ board_id: bid(m[1]), user_id: data.user.id, role: "viewer" })],
  [/^\/boards\/(\d+)\/members$/, () => [{ user_id: data.user.id, name: data.user.name, email: data.user.email, role: "admin" }]],
  [/^\/boards\/(\d+)\/invitations$/, () => []],
  [/^\/invitations\/mine$/, () => []],
  [/^\/boards\/(\d+)\/activity$/, (m) =>
    data.board_activity.filter((a) => a.board_id === bid(m[1])).reverse()],

  // SRS
  [/^\/boards\/(\d+)\/srs$/, (m, c) => pick(srsDocs(m[1]), c.params?.version)],
  [/^\/boards\/(\d+)\/srs\/versions$/, (m) =>
    srsDocs(m[1]).map(({ id, version, created_at }) => ({ id, version, created_at }))],
  [/^\/boards\/(\d+)\/srs\/export\.md$/, (m, c) =>
    new Blob([pick(srsDocs(m[1]), c.params?.version)?.markdown || ""], { type: "text/markdown" })],

  // Diagrams
  [/^\/boards\/(\d+)\/srs\/diagrams$/, (m, c) =>
    data.diagrams.filter((d) => !c.params?.srs_id || d.srs_id === Number(c.params.srs_id))],

  // Cost
  [/^\/boards\/(\d+)\/srs\/cost$/, (m) => {
    const est = data.cost_estimates.filter((e) => e.board_id === bid(m[1])).pop();
    return est ? { ...est, srs_outdated: false } : undefined;
  }],
  [/^\/boards\/(\d+)\/srs\/cost\/rates$/, () => data.cost_estimates[0]?.result?.rates_meta],

  // SDD (path guessed: adjust to your real base)
  [/^\/boards\/(\d+)\/sdd$/, (m, c) => pick(sddDocs(m[1]), c.params?.version)],
  [/^\/boards\/(\d+)\/sdd\/versions$/, (m) =>
    sddDocs(m[1]).map(({ id, version, created_at }) => ({ id, version, created_at }))],

  // Gantt (shape guessed)
  [/^\/boards\/(\d+)\/gantt$/, (m) => ({
    activities: data.activities.filter((a) => a.board_id === bid(m[1])),
    budget: data.board_budgets.find((b) => b.board_id === bid(m[1])) || null,
    increments: data.finance_increments.filter((i) => i.board_id === bid(m[1])),
    expenses: data.expenses.filter((e) => e.board_id === bid(m[1])),
  })],

  // Chat history
  [/^\/boards\/(\d+)\/chat$/, (m) => data.chat_messages.filter((c) => c.board_id === bid(m[1]))],
];

export default function demoAdapter(config) {
  const path = (config.url || "").split("?")[0].replace(/\/+$/, "") || "/";
  const method = (config.method || "get").toLowerCase();

  if (method !== "get") return fail(config, 403, "Demo mode is read-only. Backend is offline.");

  for (const [re, handler] of ROUTES) {
    const m = path.match(re);
    if (!m) continue;
    const body = handler(m, config);
    return body === undefined ? fail(config, 404, "Not found in demo data") : ok(config, body);
  }
  console.warn("[demo] unhandled GET", path);
  return fail(config, 404, "Not available in demo mode");
}