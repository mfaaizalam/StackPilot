
import axios from "axios";
import { queryClient } from "./queryClient.js";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

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
      queryClient.invalidateQueries({
        queryKey: ["board-data"],
      });

      queryClient.invalidateQueries({
        queryKey: ["trace"],
      });

      queryClient.invalidateQueries({
        queryKey: ["boards"],
      });
    }

    return response;
  },
  (error) => Promise.reject(error)
);

export default api;
