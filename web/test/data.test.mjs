// node --test: data compatibility helpers and routing (no browser needed).
import { test } from "node:test";
import assert from "node:assert/strict";
import { indexProblems, adaptLegacyCategories } from "../src/lib/data.js";
import { parseHash, formatHash } from "../src/lib/router.js";
import { groupOf } from "../src/lib/groups.js";

const filters = ["search-tech", "social", "entertainment", "shopping", "news", "reference", "work"].map((id) => ({ id }));
const fresh = {
  boards: { world: { status: "ok" }, uk: { status: "pending" }, people: { status: "ok" } },
  category_boards: { filters, months: { world: ["2026-10"] }, people_filters: [] },
};

test("a current latest.json has no problems", () => {
  assert.deepEqual(indexProblems(fresh), []);
});

test("a latest.json from before People and the merge is flagged, not treated as 'coming soon'", () => {
  const old = {
    boards: { world: { status: "ok" }, uk: { status: "pending" } },
    category_boards: { months: { world: ["2026-10"] }, filters: [{ id: "search" }, { id: "tech" }, ...filters.slice(1)] },
  };
  const p = indexProblems(old);
  assert.ok(p.includes("no people board"));
  assert.ok(p.some((x) => x.includes("search-tech")));
});

test("old search + tech category boards are merged into search-tech by raw rank", () => {
  const brands = { google: { source_rank: 1 }, apple: { source_rank: 10 }, bing: { source_rank: 40 }, github: { source_rank: 30 } };
  const month = (search, tech) => ({ brands, boards: {
    search: { sites: search.map((id, i) => ({ rank: i + 1, id })) },
    tech: { sites: tech.map((id, i) => ({ rank: i + 1, id })) },
  } });
  const out = adaptLegacyCategories({ "2026-09": month(["google"], ["github", "apple"]), "2026-10": month(["google", "bing"], ["apple"]) }, 3);
  const sep = out["2026-09"].boards["search-tech"], oct = out["2026-10"].boards["search-tech"];
  assert.deepEqual(sep.sites.map((s) => s.id), ["google", "apple", "github"]);
  assert.equal(sep.vacant, 0);
  assert.deepEqual(oct.sites.map((s) => [s.id, s.previous_rank]), [["google", 1], ["apple", 2], ["bing", null]]);
  assert.deepEqual(oct.dropped_out.map((s) => s.id), ["github"]);
});

test("current files are left alone", () => {
  const raw = { brands: {}, boards: { "search-tech": { sites: [] } } };
  assert.equal(adaptLegacyCategories({ m: raw }).m, raw);
});

test("old hashes and group keys map to the merged set", () => {
  assert.equal(formatHash(parseHash("#world/tech/2026-08/github")), "#world/search-tech/2026-08/github");
  assert.equal(formatHash(parseHash("#world/search")), "#world/search-tech");
  assert.equal(groupOf("tech_ai").label, "Search & tech");
  assert.equal(formatHash(parseHash("#people/sport/2026-07/lionel-messi")), "#people/sport/2026-07/lionel-messi");
});
