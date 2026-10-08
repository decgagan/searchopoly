// Describes month-on-month movement for a site, coping with the first month of data.
export function describeMovement(site, snapshot) {
  if (!snapshot?.has_previous_month) {
    return { symbol: "—", label: "First month tracked", detail: "No earlier month to compare", tone: "neutral" };
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

// Compact badge for squares and list rows; null when there's nothing to say.
export function badgeFor(site, snapshot) {
  if (!snapshot?.has_previous_month) return null;
  if (site.previous_rank == null) return { text: "NEW", tone: "new", label: "new this month" };
  if (!site.movement) return null;
  const n = Math.abs(site.movement);
  return site.movement > 0
    ? { text: `▲${n}`, tone: "up", label: `up ${n}` }
    : { text: `▼${n}`, tone: "down", label: `down ${n}` };
}

// Biggest climber, biggest faller, newcomers and leavers for the month.
export function summarise(snapshot) {
  if (!snapshot?.has_previous_month) return null;
  const moved = snapshot.sites.filter((s) => s.movement);
  const climber = moved.reduce((a, s) => (s.movement > 0 && (!a || s.movement > a.movement) ? s : a), null);
  const faller = moved.reduce((a, s) => (s.movement < 0 && (!a || s.movement < a.movement) ? s : a), null);
  return {
    climber,
    faller,
    newcomers: snapshot.sites.filter((s) => s.previous_rank == null),
    dropped: snapshot.dropped_out ?? [],
  };
}
