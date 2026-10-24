// Same rules as slugify() in pipeline/clean.py: fold accents to ASCII, then hyphenate.
const FOLD = { ß: "ss", ẞ: "SS", ø: "o", Ø: "O", ł: "l", Ł: "L", æ: "ae", Æ: "AE", œ: "oe", Œ: "OE",
  đ: "d", Đ: "D", ð: "d", Ð: "D", þ: "th", Þ: "Th", ı: "i", ħ: "h", Ħ: "H" };

export const asciiFold = (s) =>
  s.replace(/[ßẞøØłŁæÆœŒđĐðÐþÞıħĦ]/g, (c) => FOLD[c]).normalize("NFKD").replace(/\p{M}/gu, "");

export const slug = (s) => asciiFold(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

// Ids before October 2026 turned every accented letter into a hyphen ('nicol-s-maduro').
export const legacySlug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

// Find the entry an old-style id points at, so links shared before the change still open.
export function findLegacy(sites, id) {
  return sites.find((s) => {
    const old = legacySlug(s.name ?? s.brand ?? "");
    return old !== s.id.replace(/-q\d+$/, "") && (id === old || (s.qid && id === `${old}-${s.qid.toLowerCase()}`));
  }) ?? null;
}
