import { useQuery } from "@tanstack/react-query";
import api from "./axios.js";

// Query keys in one place so invalidation stays consistent.
export const KEYS = {
  boards: ["boards"],
  dashboardSummary: ["dashboard-summary"],
};

export const useBoards = () =>
  useQuery({
    queryKey: KEYS.boards,
    queryFn: () => api.get("/boards/").then((r) => r.data),
  });

// Works with the 3 existing endpoints today. Once a /dashboard/summary
// endpoint exists, replace the body with:
//   api.get("/dashboard/summary").then(r => r.data)
// (it should return { boards, columns, tasks, recent: [...] }).
export const useDashboardSummary = () =>
  useQuery({
    queryKey: KEYS.dashboardSummary,
    queryFn: async () => {
      const [b, c, t] = await Promise.all([
        api.get("/boards/"),
        api.get("/columns/"),
        api.get("/tasks/"),
      ]);
      return {
        boards: b.data.length,
        columns: c.data.length,
        tasks: t.data.length,
        // newest first, regardless of the order the API returns
        recent: [...b.data].sort((x, y) => y.id - x.id).slice(0, 4),
      };
    },
  });

export const useLatestSrs = (boardId) =>
  useQuery({
    queryKey: ["srs", boardId, "latest"],
    queryFn: () =>
      api.get(`/boards/${boardId}/srs/`).then((r) => r.data),
    staleTime: 60_000,
    retry: (count, err) => err?.response?.status !== 404 && count < 1,
  });