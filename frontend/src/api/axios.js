import axios from "axios";
import { queryClient } from "./queryClient.js";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Any successful write marks board/task data stale so the next visit refetches.
api.interceptors.response.use((res) => {
  const method = (res.config.method || "").toLowerCase();
  if (method !== "get") {
    queryClient.invalidateQueries({ queryKey: ["board-data"] });
    queryClient.invalidateQueries({ queryKey: ["trace"] });
  }
  return res;
});

export default api;