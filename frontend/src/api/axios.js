
import axios from "axios";

const api = axios.create({
<<<<<<< HEAD
  baseURL: "https://stackpilot-production-f425.up.railway.app",
=======
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
>>>>>>> 5248603f31439c0d4db9f9e2d6851fc11bac3a97
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
// https://stackpilot-production-f425.up.railway.app/