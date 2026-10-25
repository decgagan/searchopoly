// URL hash state. Category filter and month are optional ("all sites", "latest" when absent).
//   #world                         World board, latest month
//   #uk/2026-09                    UK board, September 2026
//   #world/2026-09/google          ...with Google's site card open
//   #world/google                  latest month with a card open
//   #world/shopping                World Shopping board (one colour set)
//   #world/shopping/2026-08/amazon ...for August 2026 with Amazon's card open
//   #world/search, #world/tech     old slugs, redirected to #world/search-tech
//   #people                        Most viewed people (Wikipedia), latest complete month
//   #people/sport/2026-09/<person> ...one colour set, a month and a person's card
//   #about                         "How it's made" page
//   #og                            share-image layout (used by scripts/og-image.mjs)
import { FILTER_IDS, FILTER_ALIASES, UK_FILTER_ALIASES } from "./groups.js";

export const BOARDS = ["world", "uk", "people"];
export const PAGES = ["about", "og"];
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;

export function parseHash(hash) {
  const parts = hash.replace(/^#\/?/, "").toLowerCase().split("/").filter(Boolean);
  const blank = { page: "board", board: "world", filter: null, month: null, site: null };
  if (PAGES.includes(parts[0])) return { ...blank, page: parts[0] };
  let board = "world";
  if (BOARDS.includes(parts[0])) board = parts.shift();
  else if (parts.length) return blank; // unknown hash
  if (board === "uk" && UK_FILTER_ALIASES[parts[0]]) parts[0] = UK_FILTER_ALIASES[parts[0]];
  else if (board !== "people" && FILTER_ALIASES[parts[0]]) parts[0] = FILTER_ALIASES[parts[0]];
  const filter = FILTER_IDS.includes(parts[0]) ? parts.shift() : null;
  const month = parts[0] && MONTH.test(parts[0]) ? parts.shift() : null;
  const site = parts[0] ? decodeURIComponent(parts[0]) : null;
  return { page: "board", board, filter, month, site };
}

export function formatHash({ page = "board", board, filter = null, month, site }) {
  if (page !== "board") return `#${page}`;
  const parts = [board];
  if (filter) parts.push(filter);
  if (month) parts.push(month);
  if (site) parts.push(encodeURIComponent(site));
  return parts.length === 1 && board === "world" ? "" : `#${parts.join("/")}`;
}
