// The 8 colour sets. Keys match the `group` column in pipeline/data/categories.csv.
export const GROUPS = {
  search_portals: { label: "Search & portals", colour: "#3b5bdb" },
  social_messaging: { label: "Social & messaging", colour: "#d6336c" },
  entertainment: { label: "Entertainment", colour: "#7048e8" },
  shopping: { label: "Shopping", colour: "#b25900" },
  news_sport: { label: "News & sport", colour: "#d42c2c" },
  reference_learning: { label: "Reference & learning", colour: "#09845f" },
  tech_ai: { label: "Tech & AI", colour: "#0d7f91" },
  work_money: { label: "Work & money", colour: "#546170" },
};

export const FALLBACK = { label: "Other", colour: "#868e96" };

export const groupOf = (key) => GROUPS[key] ?? FALLBACK;

// Category boards: URL slug -> colour set, in board order. Must match CATEGORY_BOARDS in
// pipeline/config.py (the pipeline writes the same list to latest.json).
export const FILTERS = [
  { id: "search", group: "search_portals" },
  { id: "social", group: "social_messaging" },
  { id: "entertainment", group: "entertainment" },
  { id: "shopping", group: "shopping" },
  { id: "news", group: "news_sport" },
  { id: "reference", group: "reference_learning" },
  { id: "tech", group: "tech_ai" },
  { id: "work", group: "work_money" },
].map((f) => ({ ...f, label: GROUPS[f.group].label, colour: GROUPS[f.group].colour }));

export const FILTER_IDS = FILTERS.map((f) => f.id);
export const filterOf = (id) => FILTERS.find((f) => f.id === id) ?? null;
