// Renders PNG app icons from public/favicon.svg. One-off: outputs are committed.
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import { findChrome } from "./shoot.mjs";

const pub = resolve(dirname(fileURLToPath(import.meta.url)), "../public");
const svg = readFileSync(resolve(pub, "favicon.svg"), "utf8");
const browser = await chromium.launch({ executablePath: findChrome(), args: ["--no-sandbox"] });
const page = await browser.newPage();
for (const [name, size, pad, bg] of [
  ["favicon-32.png", 32, 0, "transparent"],
  ["apple-touch-icon.png", 180, 0, "#101828"],
  ["icon-192.png", 192, 0, "transparent"],
  ["icon-512.png", 512, 0, "transparent"],
  ["icon-maskable-512.png", 512, 64, "#101828"],
]) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(
    `<html><body style="margin:0;background:${bg}"><div style="width:${size}px;height:${size}px;padding:${pad}px;box-sizing:border-box">${svg.replace("<svg ", '<svg width="100%" height="100%" ')}</div></body></html>`
  );
  await page.screenshot({ path: resolve(pub, name), omitBackground: bg === "transparent" });
  console.log(`icons: ${name}`);
}
await browser.close();
