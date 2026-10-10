export function monthLabel(month) {
  if (!month) return "";
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString("en-GB", {
    month: "long", year: "numeric", timeZone: "UTC",
  });
}

const compact = new Intl.NumberFormat("en-GB", { notation: "compact", maximumFractionDigits: 1 });
// 8522591 -> "8.5M"
export const compactNumber = (n) => compact.format(n);

// Wikidata dates come at day, month or year precision: "1927-06-01", "1927-06" or "1927".
export function dateLabel(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  if (!m) return String(y);
  const date = new Date(Date.UTC(y, m - 1, d || 1));
  return date.toLocaleDateString("en-GB", {
    ...(d ? { day: "numeric" } : {}), month: "long", year: "numeric", timeZone: "UTC",
  });
}

export function dayLabel(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}
