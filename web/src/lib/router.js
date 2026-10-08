// URL hash state. Month is optional and means "latest" when absent.
//   #world               World board, latest month
//   #uk/2026-09          UK board, September 2026
//   #world/2026-09/google  ...with Google's site card open
//   #world/google        latest month with a card open
export const BOARDS = ["world", "uk"];
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;

export function parseHash(hash) {
  const parts = hash.replace(/^#\/?/, "").toLowerCase().split("/").filter(Boolean);
  let board = "world";
  if (BOARDS.includes(parts[0])) board = parts.shift();
  else if (parts.length) return { board, month: null, site: null }; // unknown hash: ignore it
  const month = parts[0] && MONTH.test(parts[0]) ? parts.shift() : null;
  const site = parts[0] ? decodeURIComponent(parts[0]) : null;
  return { board, month, site };
}

export function formatHash({ board, month, site }) {
  const parts = [board];
  if (month) parts.push(month);
  if (site) parts.push(encodeURIComponent(site));
  return parts.length === 1 && board === "world" ? "" : `#${parts.join("/")}`;
}
