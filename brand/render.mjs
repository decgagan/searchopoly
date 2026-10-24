// Renders the X profile assets with headless Chrome. Run from the repo root:
//   node brand/render.mjs [outDir]     (default ../searchopoly-account/brand)
// Board screenshots for the launch image come from the live site (https://searchopoly.co.uk).
import { readFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "..");
const { chromium } = createRequire(resolve(repo, "web/package.json"))("playwright-core");
const { findChrome } = await import(pathToFileURL(resolve(repo, "web/scripts/shoot.mjs")));
const out = resolve(process.argv[2] ?? resolve(repo, "../searchopoly-account/brand"));
const tmp = resolve(here, "out"); // gitignored scratch
mkdirSync(out, { recursive: true }); mkdirSync(tmp, { recursive: true });
const SITE = "https://searchopoly.co.uk";
const groupsSrc = readFileSync(resolve(repo, "web/src/lib/groups.js"), "utf8");
const groups = Object.fromEntries([...groupsSrc.matchAll(/(\w+): \{ label: "[^"]+", colour: "(#[0-9a-f]{6})"/g)].map((m) => [m[1], m[2]]));
const world = JSON.parse(readFileSync(resolve(repo, "data/snapshots/2026-10/world.json"), "utf8"));

const browser = await chromium.launch({ executablePath: findChrome() });
const shot = async (file, w, h, path, prep) => {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.goto(pathToFileURL(resolve(here, file)).href);
  if (prep) await page.evaluate(prep.fn, prep.arg);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path });
  return page;
};
try {
  // 1. Avatar + 48px circular preview
  await shot("avatar.html", 400, 400, resolve(out, "avatar-400.png"));
  const prev = await browser.newPage({ viewport: { width: 48, height: 48 }, deviceScaleFactor: 1 });
  const b64 = readFileSync(resolve(out, "avatar-400.png")).toString("base64");
  await prev.setContent(`<body style="margin:0;background:transparent"><img src="data:image/png;base64,${b64}" style="width:48px;height:48px;border-radius:50%;display:block">`);
  await prev.screenshot({ path: resolve(out, "avatar-preview-48.png"), omitBackground: true });

  // 2. Header + safe-zone preview
  const hp = await shot("header.html", 1500, 500, resolve(out, "header-1500x500.png"),
    { fn: (a) => window.render(a), arg: { sites: world.sites.slice(0, 9), groups } });
  await hp.evaluate(() => document.body.insertAdjacentHTML("beforeend", `
    <div style="position:absolute;inset:0 0 auto 0;height:60px;background:rgba(255,0,0,.35)"></div>
    <div style="position:absolute;inset:auto 0 0 0;height:60px;background:rgba(255,0,0,.35)"></div>
    <div style="position:absolute;left:0;bottom:0;width:200px;height:150px;background:rgba(255,0,0,.5);outline:3px dashed #fff;color:#fff;font:700 16px sans-serif;display:grid;place-items:center">avatar overlap</div>`));
  await hp.screenshot({ path: resolve(out, "header-safe-zones-preview.png") });

  // 3. Launch image from live board screenshots
  for (const [name, hash] of [["world", "#world/2026-10"], ["people", "#people/2026-09"]]) {
    const p = await browser.newPage({ viewport: { width: 1000, height: 1000 }, deviceScaleFactor: 1, reducedMotion: "reduce" });
    await p.goto(`${SITE}/${hash}`);
    await p.waitForSelector("button.square:visible");
    await p.waitForTimeout(1500);
    await p.evaluate(() => document.fonts.ready);
    await p.locator(".board").first().screenshot({ path: resolve(tmp, `board-${name}.png`) });
  }
  await shot("launch.html", 1200, 675, resolve(out, "launch-1200x675.png"));
} finally { await browser.close(); }
console.log(`brand: wrote assets to ${out}`);
