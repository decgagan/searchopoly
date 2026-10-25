// The 7 colour sets. Keys match the `group` column in pipeline/data/categories.csv.
// "Search & tech" merges what used to be two sets (search & portals, tech & AI).
export const GROUPS = {
  search_tech: { label: "Search & tech", colour: "#3b5bdb" },
  social_messaging: { label: "Social & messaging", colour: "#d6336c" },
  entertainment: { label: "Entertainment", colour: "#7048e8" },
  shopping: { label: "Shopping", colour: "#b25900" },
  news_sport: { label: "News & sport", colour: "#d42c2c" },
  reference_learning: { label: "Reference & learning", colour: "#09845f" },
  work_money: { label: "Work & money", colour: "#546170" },
};

export const FALLBACK = { label: "Other", colour: "#868e96" };

// The People board's 7 colour sets, from Wikidata occupations. Keys match PEOPLE_CATEGORIES
// in pipeline/people.py (the pipeline writes the same list to latest.json).
export const PEOPLE_GROUPS = {
  politics: { label: "Politics", colour: "#1c4fc4" },
  royalty: { label: "Royalty", colour: "#8a6100" },
  sport: { label: "Sport", colour: "#2b7a35" },
  music: { label: "Music", colour: "#c2255c" },
  screen: { label: "Film, TV & media", colour: "#6741d9" },
  business: { label: "Business & tech", colour: "#0b7285" },
  other: { label: "Other", colour: "#5c6370" },
};

// Group keys from before the merge, in case older data turns up next to this code.
const GROUP_ALIASES = { search_portals: "search_tech", tech_ai: "search_tech" };

export const groupOf = (key) => GROUPS[GROUP_ALIASES[key] ?? key] ?? PEOPLE_GROUPS[key] ?? FALLBACK;
export const groupsFor = (board) => (board === "people" ? PEOPLE_GROUPS : GROUPS);

// Category boards: URL slug -> colour set, in board order. Must match CATEGORY_BOARDS in
// pipeline/config.py (the pipeline writes the same list to latest.json).
export const FILTERS = [
  { id: "search-tech", group: "search_tech" },
  { id: "social", group: "social_messaging" },
  { id: "entertainment", group: "entertainment" },
  { id: "shopping", group: "shopping" },
  { id: "news", group: "news_sport" },
  { id: "reference", group: "reference_learning" },
  { id: "work", group: "work_money" },
].map((f) => ({ ...f, label: GROUPS[f.group].label, colour: GROUPS[f.group].colour }));

export const PEOPLE_FILTERS = Object.entries(PEOPLE_GROUPS).map(([id, g]) => ({ id, group: id, ...g }));

export const filtersFor = (board) => (board === "people" ? PEOPLE_FILTERS : board === "world" || board === "uk" ? FILTERS : []);
export const FILTER_IDS = [...FILTERS, ...PEOPLE_FILTERS].map((f) => f.id);
// Slugs from before Search & portals and Tech & AI merged; old links still work.
export const FILTER_ALIASES = { search: "search-tech", tech: "search-tech" };
export const filterOf = (id, board = "world") => filtersFor(board).find((f) => f.id === id) ?? null;
