// Describes month-on-month movement for a site, coping with the first month of data.
export function describeMovement(site, snapshot) {
  if (!snapshot?.has_previous_month) {
    return { symbol: "—", label: "First month tracked", detail: "Movement appears from next month", tone: "neutral" };
  }
  if (site.previous_rank == null) {
    return { symbol: "★", label: "New this month", detail: "Not on last month's board", tone: "new" };
  }
  if (!site.movement) {
    return { symbol: "=", label: "No change", detail: `Also #${site.previous_rank} last month`, tone: "neutral" };
  }
  const n = Math.abs(site.movement);
  const places = `${n} place${n === 1 ? "" : "s"}`;
  return site.movement > 0
    ? { symbol: "▲", label: `Up ${places}`, detail: `From #${site.previous_rank}`, tone: "up" }
    : { symbol: "▼", label: `Down ${places}`, detail: `From #${site.previous_rank}`, tone: "down" };
}
