import axios from "axios";

const api = axios.create({ baseURL: "http://localhost:8000/api" });

// Gautham's and Devika's routes end with "/", Athul's don't.
const NEEDS_SLASH = ["/subscriptions", "/invoices", "/templates", "/payments", "/taxes", "/discounts"];

api.interceptors.request.use((config) => {
  const url = config.url || "";
  if (NEEDS_SLASH.includes(url)) config.url = url + "/";

  const token = localStorage.getItem("token");
  if (token && token !== "demo" && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url || "";
    if (error.response?.status === 401 && url.startsWith("/auth/me")) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export { api };
export default api;