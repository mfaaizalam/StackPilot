import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "./axios.js";

export const ganttKey = (boardId) => ["gantt", String(boardId)];

// One call returns activities + metrics + finance summary + alerts + phases.
export const useGantt = (boardId) =>
  useQuery({
    queryKey: ganttKey(boardId),
    queryFn: () => api.get(`/boards/${boardId}/gantt`).then((r) => r.data),
    staleTime: 15_000,
    retry: (count, err) => ![401, 403, 404].includes(err?.response?.status) && count < 1,
  });

// Every write refreshes the single /gantt payload, so cards, chart and alerts always agree.
export function useGanttActions(boardId) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: ganttKey(boardId) });
  const b = `/boards/${boardId}`;
  const mut = (fn) => useMutation({ mutationFn: fn, onSuccess: refresh });
  return {
    addActivity: mut((body) => api.post(`${b}/activities`, body).then((r) => r.data)),
    updateActivity: mut(({ id, patch }) => api.patch(`${b}/activities/${id}`, patch).then((r) => r.data)),
    deleteActivity: mut((id) => api.delete(`${b}/activities/${id}`)),
    seed: mut((mode) => api.post(`${b}/activities/seed`, { mode }).then((r) => r.data)),
    setBudget: mut((base_budget) => api.put(`${b}/budget`, { base_budget }).then((r) => r.data)),
    addIncrement: mut((body) => api.post(`${b}/finance-increments`, body).then((r) => r.data)),
    updateIncrement: mut(({ id, patch }) => api.patch(`${b}/finance-increments/${id}`, patch).then((r) => r.data)),
    deleteIncrement: mut((id) => api.delete(`${b}/finance-increments/${id}`)),
  };
}
