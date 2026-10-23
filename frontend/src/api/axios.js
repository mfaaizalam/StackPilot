import axios from "axios";
import { queryClient } from "./queryClient.js";
import { isDemo } from "../demo/demoMode.js";
import demoAdapter from "../demo/demoAdapter.js";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://stackpilot-production-5297.up.railway.app",
  headers: {
    "Content-Type": "application/json",
  },
});

// In demo mode, answer requests from local JSON instead of hitting the backend.
const realAdapter = axios.getAdapter(axios.defaults.adapter);
api.defaults.adapter = (config) => (isDemo() ? demoAdapter(config) : realAdapter(config));

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");

    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => {
    const method = (response.config.method || "").toLowerCase();

    if (method && method !== "get") {
      queryClient.invalidateQueries({ queryKey: ["board-data"] });
      queryClient.invalidateQueries({ queryKey: ["trace"] });
      queryClient.invalidateQueries({ queryKey: ["boards"] });
    }

    return response;
  },
  (error) => Promise.reject(error)
);

export default api;