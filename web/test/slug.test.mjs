import { test } from "node:test";
import assert from "node:assert/strict";
import { slug, legacySlug, findLegacy } from "../src/lib/slug.js";

test("slug folds accents like the pipeline", () => {
  assert.equal(slug("Nicolás Maduro"), "nicolas-maduro");
  assert.equal(slug("Johannes Høsflot Klæbo"), "johannes-hosflot-klaebo");
  assert.equal(slug("Straße Łódź"), "strasse-lodz");
  assert.equal(slug("X (Twitter)"), "x-twitter");
  assert.equal(legacySlug("Nicolás Maduro"), "nicol-s-maduro");
});

test("old accent-hyphen ids resolve to the new entry", () => {
  const sites = [{ id: "lionel-messi", name: "Lionel Messi" }, { id: "nicolas-maduro", name: "Nicolás Maduro", qid: "Q58132" },
    { id: "celine-dion-q5105", name: "Céline Dion", qid: "Q5105" }];
  assert.equal(findLegacy(sites, "nicol-s-maduro")?.id, "nicolas-maduro");
  assert.equal(findLegacy(sites, "c-line-dion-q5105")?.id, "celine-dion-q5105");
  assert.equal(findLegacy(sites, "nobody"), null);
});
