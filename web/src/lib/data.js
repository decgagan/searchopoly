// Loading the pipeline's JSON safely across deploys.
import { FILTERS, PEOPLE_FILTERS, FILTER_ALIASES } from "./groups.js";

/* global __DATA_VERSION__ */
export const DATA_VERSION = typeof __DATA_VERSION__ === "undefined" ? "dev" : __DATA_VERSION__;
const BASE = `${import.meta.env?.BASE_URL ?? "/"}data`;

// Every URL carries the data version, so an older cached copy is never reused. "no-cache"
// still lets the browser revalidate cheaply (ETag, 304) instead of downloading again.
export async function getJSON(path, { reload = false } = {}) {
  const v = reload ? `${DATA_VERSION}-${Date.now()}` : DATA_VERSION;
  const res = await fetch(`${BASE}/${path}?v=${v}`, { cache: reload ? "reload" : "no-cache" });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

// What this bundle expects from latest.json. Anything missing means the data is older than
// the code (a stale cache or a half-finished deploy), not that a board is "coming soon".
export function indexProblems(index) {
  const problems = [];
  for (const board of ["world", "people"]) {
    if (!index?.boards?.[board]) problems.push(`no ${board} board`);
  }
  const cb = index?.category_boards;
  if (cb?.months?.world?.length) {
    const ids = new Set((cb.filters ?? []).map((f) => f.id));
    const missing = FILTERS.filter((f) => !ids.has(f.id)).map((f) => f.id);
    if (missing.length) problems.push(`no category boards for ${missing.join(", ")}`);
  }
  if (index?.boards?.people && !cb?.people_filters) problems.push("no People colour sets");
  return problems;
}

// Old category files (before Search & portals and Tech & AI merged) have "search" and "tech"
// boards but no "search-tech". Rebuild the merged board from them: same brands, ranked by
// raw rank, top 28, with movement recomputed month to month.
export function adaptLegacyCategories(byMonth, boardSize = 28) {
  const legacy = Object.entries(FILTER_ALIASES).filter(([, to]) => to === "search-tech").map(([from]) => from);
  let prev = null;
  for (const m of Object.keys(byMonth).sort()) {
    const raw = byMonth[m];
    if (!raw?.boards || raw.boards["search-tech"] || !legacy.some((k) => raw.boards[k])) {
      prev = raw?.boards?.["search-tech"] ?? null;
      continue;
    }
    const seen = new Set();
    const ids = legacy.flatMap((k) => raw.boards[k]?.sites ?? []).map((s) => s.id)
      .filter((id) => !seen.has(id) && seen.add(id))
      .sort((a, b) => (raw.brands[a]?.source_rank ?? 1e9) - (raw.brands[b]?.source_rank ?? 1e9))
      .slice(0, boardSize);
    const before = new Map((prev?.sites ?? []).map((s) => [s.id, s.rank]));
    const sites = ids.map((id, i) => {
      const previous = before.get(id) ?? null;
      return { rank: i + 1, id, previous_rank: previous, movement: previous ? previous - (i + 1) : null };
    });
    const now = new Set(ids);
    const board = {
      sites,
      vacant: Math.max(0, boardSize - sites.length),
      dropped_out: (prev?.sites ?? []).filter((s) => !now.has(s.id)).map((s) => ({ ...(raw.brands[s.id] ?? {}), id: s.id, previous_rank: s.rank })),
    };
    raw.boards = { "search-tech": board, ...raw.boards };
    prev = board;
  }
  return byMonth;
}

export const PEOPLE_FILTER_IDS = PEOPLE_FILTERS.map((f) => f.id);
