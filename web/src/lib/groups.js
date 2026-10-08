// The 8 colour sets. Keys match the `group` column in pipeline/data/categories.csv.
export const GROUPS = {
  search_portals: { label: "Search & portals", colour: "#3b5bdb" },
  social_messaging: { label: "Social & messaging", colour: "#d6336c" },
  entertainment: { label: "Entertainment", colour: "#7048e8" },
  shopping: { label: "Shopping", colour: "#f08c00" },
  news_sport: { label: "News & sport", colour: "#e03131" },
  reference_learning: { label: "Reference & learning", colour: "#0ca678" },
  tech_ai: { label: "Tech & AI", colour: "#1098ad" },
  work_money: { label: "Work & money", colour: "#9c5b2e" },
};

export const FALLBACK = { label: "Other", colour: "#868e96" };

export const groupOf = (key) => GROUPS[key] ?? FALLBACK;
