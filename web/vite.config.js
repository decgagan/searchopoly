import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// A short hash of every data JSON file, baked into the bundle. The app adds it to every data
// URL (?v=...), so a browser can never pair this bundle with data cached from an older deploy.
function dataVersion(dir = "../data") {
  const hash = createHash("sha256");
  const walk = (d) => {
    for (const name of readdirSync(d).sort()) {
      const p = join(d, name);
      if (statSync(p).isDirectory()) walk(p);
      else if (name.endsWith(".json")) hash.update(relative(dir, p)).update(readFileSync(p));
    }
  };
  try { walk(dir); } catch { return "dev"; }
  return hash.digest("hex").slice(0, 12);
}

// No-JavaScript fallback: the latest World and UK rankings as plain tables, baked into
// index.html at build time from the same snapshot files the app loads.
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
function noscriptTables(dir = "../data") {
  try {
    const index = JSON.parse(readFileSync(join(dir, "latest.json"), "utf8"));
    const out = [];
    for (const [key, title] of [["world", "Most visited websites worldwide"], ["uk", "Most visited websites in the UK"]]) {
      const info = index.boards?.[key];
      if (info?.status !== "ok") continue;
      const snap = JSON.parse(readFileSync(join(dir, info.latest), "utf8"));
      const [y, m] = snap.month.split("-").map(Number);
      const when = new Date(Date.UTC(y, m - 1, 1)).toLocaleString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
      const rows = snap.sites.map((s) => `<tr><td>${s.rank}</td><td>${esc(s.brand)}</td><td>${esc(s.domain)}</td></tr>`).join("");
      out.push(`<h2>${title}, ${when}</h2><table style="border-collapse:collapse;width:100%"><thead><tr><th align="left">Rank</th><th align="left">Site</th><th align="left">Domain</th></tr></thead><tbody>${rows}</tbody></table><p><small>Source: ${esc(snap.source?.name ?? "")}.</small></p>`);
    }
    return out.join("\n");
  } catch { return ""; }
}

export default defineConfig({
  plugins: [svelte(), { name: "noscript-tables", transformIndexHtml: (html) => html.replace("<!--NOSCRIPT_TABLES-->", noscriptTables()) }],
  define: { __DATA_VERSION__: JSON.stringify(dataVersion()) },
});
