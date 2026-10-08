// Shared helpers: serve the production build and drive the system Chrome with playwright-core.
import { existsSync } from "node:fs";
import { preview } from "vite";
import { chromium } from "playwright-core";

const CANDIDATES = [
  process.env.CHROME_PATH,
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

export function findChrome() {
  const path = CANDIDATES.find((p) => existsSync(p));
  if (!path) throw new Error("No Chrome/Chromium found. Set CHROME_PATH.");
  return path;
}

export async function withPreview(fn) {
  const server = await preview({ preview: { port: 4321, strictPort: false }, logLevel: "warn" });
  const url = server.resolvedUrls.local[0];
  const browser = await chromium.launch({ executablePath: findChrome(), args: ["--no-sandbox"] });
  try {
    return await fn(browser, url);
  } finally {
    await browser.close();
    await new Promise((r) => server.httpServer.close(r));
  }
}
