// Thin fetch wrapper around the FastAPI backend.
//
// In dev, Vite proxies /api and /images to http://127.0.0.1:8000 (see
// vite.config.js), so relative paths work with zero configuration. In
// a production build you can still point this at a different host by
// setting VITE_API_BASE_URL in a .env file next to package.json.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(detail || `Request to ${path} failed (${res.status})`);
  }

  if (res.status === 204) return null;
  return res.json();
}

export function getSetup() {
  return request("/api/setup");
}

export function getDocuments() {
  return request("/api/documents");
}

export function getDashboard() {
  return request("/api/dashboard");
}

export function uploadDocuments(files) {
  const formData = new FormData();
  for (const file of files) formData.append("files", file);

  return request("/api/documents", {
    method: "POST",
    body: formData,
  });
}

export function deleteDocument(name) {
  return request(`/api/documents/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

export function resetDocuments() {
  return request("/api/documents/reset", { method: "POST" });
}

export function sendChat(question) {
  return request("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export function imageSrc(path) {
  if (!path) return "";
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}
