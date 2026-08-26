// Thin fetch wrappers over the frozen API contract (docs/api-contract.md).
// The dashboard NEVER talks to the model or dataset directly — the FastAPI
// service (and the one serialized pipeline behind it) is the only backend.

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function getJson(path) {
  // 5 s timeout: a hung request must not stall the polling loop forever —
  // fail this tick, show the disconnected banner, retry on the next tick.
  const response = await fetch(`${API_BASE}${path}`, {
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) {
    throw new Error(`${path} -> HTTP ${response.status}`);
  }
  return response.json();
}

export const fetchHealth = () => getJson("/health");
export const fetchStats = () => getJson("/stats");

// The feed shows at most a few dozen rows; 50 (the contract default) is
// plenty and keeps the 2 s polling payload small.
export const fetchRecentFeed = () => getJson("/predictions/recent?limit=50");
