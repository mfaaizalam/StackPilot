import axios from "axios";

const api = axios.create({
  baseURL: "https://stackpilot-production-f425.up.railway.app",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
// https://stackpilot-production-f425.up.railway.app/