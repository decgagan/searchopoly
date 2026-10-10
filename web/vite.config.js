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

export default defineConfig({
  plugins: [svelte()],
  define: { __DATA_VERSION__: JSON.stringify(dataVersion()) },
});
