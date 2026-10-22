import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "./axios.js";
import { ganttKey } from "./gantt.js";

const base = (boardId) => `/boards/${boardId}/deployment`;
export const depKey = (boardId, ...rest) => ["deployment", String(boardId), ...rest];

export const useDeploymentOptions = (boardId) =>
  useQuery({ queryKey: depKey(boardId, "options"), queryFn: () => api.get(`${base(boardId)}/options`).then((r) => r.data), staleTime: 5 * 60_000 });

export const usePlans = (boardId) =>
  useQuery({ queryKey: depKey(boardId, "plans"), queryFn: () => api.get(`${base(boardId)}/plans`).then((r) => r.data) });

export const usePlan = (boardId, planId) =>
  useQuery({ queryKey: depKey(boardId, "plan", planId), enabled: !!planId, queryFn: () => api.get(`${base(boardId)}/plans/${planId}`).then((r) => r.data) });

export const useDocs = (boardId) =>
  useQuery({ queryKey: depKey(boardId, "docs"), queryFn: () => api.get(`${base(boardId)}/docs`).then((r) => r.data) });

export const useSuggest = (boardId) =>
  useMutation({ mutationFn: (stack) => api.post(`${base(boardId)}/suggest`, stack).then((r) => r.data) });

export function useDeploymentActions(boardId) {
  const qc = useQueryClient();
  const refresh = () => {
    qc.invalidateQueries({ queryKey: depKey(boardId) });
    qc.invalidateQueries({ queryKey: ganttKey(boardId) });   // adding hosting to Costing changes its totals
  };
  const mut = (fn) => useMutation({ mutationFn: fn, onSuccess: refresh });
  return {
    generate: mut((body) => api.post(`${base(boardId)}/generate`, body).then((r) => r.data)),
    addDoc: mut((body) => api.post(`${base(boardId)}/docs`, body).then((r) => r.data)),
    updateDoc: mut(({ id, patch }) => api.patch(`${base(boardId)}/docs/${id}`, patch).then((r) => r.data)),
    addToCosting: mut(({ planId, months }) => api.post(`${base(boardId)}/plans/${planId}/add-to-costing`, { months }).then((r) => r.data)),
    deleteDoc: mut((id) => api.delete(`${base(boardId)}/docs/${id}`)),
  };
}
