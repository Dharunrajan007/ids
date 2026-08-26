// Pure presentation logic — kept out of components so vitest can cover it
// without a DOM. Everything here must survive malformed/partial API data:
// the UI degrades, it never crashes.

// Known attack categories (frozen taxonomy). `fallback` handles a category
// this build has never heard of — render it honestly instead of crashing.
export const ATTACK_META = {
  dos: { label: "DoS", color: "#f0433c" },
  probe: { label: "Probe", color: "#f59f0b" },
  r2l: { label: "R2L", color: "#e14fd0" },
  u2r: { label: "U2R", color: "#8b5cf6" },
};

export function attackMeta(type) {
  return ATTACK_META[type] ?? { label: String(type ?? "unknown"), color: "#64748b" };
}

export function confidencePercent(confidence) {
  const value = Number(confidence);
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

// "2026-08-26T17:43:08Z" -> "17:43:08" (timestamps are UTC per contract;
// the header labels the feed as UTC once instead of repeating Z everywhere).
export function timeOfDay(timestamp) {
  if (typeof timestamp !== "string" || timestamp.length < 19) return "—";
  return timestamp.slice(11, 19);
}

// /stats attacks_by_type -> Recharts rows. Includes any unexpected extra
// keys the API might one day send, so the chart never silently drops data.
export function buildTypeChartData(attacksByType) {
  return Object.entries(attacksByType ?? {}).map(([type, count]) => ({
    type,
    label: attackMeta(type).label,
    count: Number(count) || 0,
    color: attackMeta(type).color,
  }));
}

// /stats traffic_timeline -> Recharts rows (defensive copy with defaults).
export function buildTimelineData(timeline) {
  if (!Array.isArray(timeline)) return [];
  return timeline.map((entry) => ({
    minute: entry?.minute ?? "—",
    normal: Number(entry?.normal) || 0,
    attack: Number(entry?.attack) || 0,
  }));
}

export function alertsFrom(records) {
  if (!Array.isArray(records)) return [];
  return records.filter((record) => record?.prediction === "attack");
}

// Value-based record identity. Polling replaces the feed array with fresh
// objects every 2 s, so `record === selected` stops matching one tick after
// a click and the highlight vanishes; comparing the fields that identify a
// record keeps the selection stable across polls. (Two byte-identical flows
// in the same second are indistinguishable — then both rows highlight,
// which is honest.)
export function sameRecord(a, b) {
  return Boolean(
    a && b
    && a.timestamp === b.timestamp
    && a.prediction === b.prediction
    && a.attack_type === b.attack_type
    && a.confidence === b.confidence
    && a.features?.service === b.features?.service
    && a.features?.src_bytes === b.features?.src_bytes,
  );
}
