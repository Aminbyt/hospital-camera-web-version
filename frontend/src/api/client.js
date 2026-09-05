export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res;
}

export const api = {
  health: () => request("/api/health"),
  cameras: {
    list: () => request("/api/cameras"),
    create: (data) => request("/api/cameras", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) => request(`/api/cameras/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id) => request(`/api/cameras/${id}`, { method: "DELETE" }),
    calibrate: (id) => request(`/api/cameras/${id}/calibrate`, { method: "POST" }),
    status: (id) => request(`/api/cameras/${id}/status`),
  },
  events: {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/events${qs ? `?${qs}` : ""}`);
    },
    exportUrl: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return `${API_BASE}/api/events/export${qs ? `?${qs}` : ""}`;
    },
  },
  alerts: {
    list: () => request("/api/alerts"),
  },
  settings: {
    get: () => request("/api/settings"),
    update: (values) => request("/api/settings", { method: "PUT", body: JSON.stringify({ values }) }),
  },
  registration: {
    capture: (data) => request("/api/registration/capture", { method: "POST", body: JSON.stringify(data) }),
    staff: () => request("/api/registration/staff"),
    resetCache: () => request("/api/registration/reset-cache", { method: "POST" }),
  },
  // FIX: this must match the actual FastAPI route in routers/stream.py, which is
  // mounted at prefix "/api/stream" with path "/sink/{camera_id}/live" — the old
  // version pointed at "/api/stream/{id}", which 404s and never renders anything.
  streamUrl: (id) => `${API_BASE}/api/stream/sink/${id}/live`,
};