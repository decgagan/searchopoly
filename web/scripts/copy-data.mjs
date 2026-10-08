// Copies the pipeline output (../data) into public/data so Vite serves and bundles it.
// Runs automatically before `npm run dev` and `npm run build`.
import { cpSync, existsSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../data");
const dest = resolve(here, "../public/data");

if (!existsSync(resolve(src, "latest.json"))) {
  console.error(`copy-data: ${src}/latest.json not found. Run "python -m pipeline.run" first.`);
  process.exit(1);
}
rmSync(dest, { recursive: true, force: true });
// JSON only: the transparency CSVs stay in the repo, not on the site.
cpSync(src, dest, { recursive: true, filter: (p) => !p.endsWith(".csv") });
console.log(`copy-data: ${src} -> ${dest}`);
