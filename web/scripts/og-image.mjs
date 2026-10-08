// Renders the share image (public/og.png, 1200x630) from the current snapshot.
// Needs a production build first: `npm run build && npm run og`. The monthly workflow runs it.
import { copyFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { withPreview } from "./shoot.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = resolve(root, "public/og.png");

await withPreview(async (browser, url) => {
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, reducedMotion: "reduce" });
  await page.goto(`${url}#og`);
  await page.waitForSelector("[data-og-ready]");
  await page.evaluate(() => document.fonts.ready);
  await page.locator(".og").screenshot({ path: out });
});
copyFileSync(out, resolve(root, "dist/og.png")); // keep the current build in step
console.log(`og-image: wrote ${out}`);
