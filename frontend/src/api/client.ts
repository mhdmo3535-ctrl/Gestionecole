import axios, { AxiosError } from "axios";

export const TOKEN_KEY = "schoolaris_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

/** Message d'erreur lisible renvoyé par FastAPI ({detail: "..."}). */
export function messageErreur(error: unknown, secours = "Une erreur est survenue."): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const premier = detail[0] as { msg?: string };
      if (premier?.msg) return premier.msg;
    }
    if (error.code === "ERR_NETWORK") return "Impossible de joindre le serveur.";
  }
  return secours;
}
