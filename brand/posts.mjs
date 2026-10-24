// Renders 1200x675 post images from repo data + live card screenshots.
//   node brand/posts.mjs [outDir]   (default ../searchopoly-account/post-images)
import { readFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "..");
const { chromium } = createRequire(resolve(repo, "web/package.json"))("playwright-core");
const { findChrome } = await import(pathToFileURL(resolve(repo, "web/scripts/shoot.mjs")));
const out = resolve(process.argv[2] ?? resolve(repo, "../searchopoly-account/post-images"));
const tmp = resolve(here, "out");
mkdirSync(out, { recursive: true }); mkdirSync(tmp, { recursive: true });
const SITE = "https://searchopoly.co.uk";
const snap = (m, f) => JSON.parse(readFileSync(resolve(repo, `data/snapshots/${m}/${f}.json`), "utf8"));
const groupsSrc = readFileSync(resolve(repo, "web/src/lib/groups.js"), "utf8");
const COL = Object.fromEntries([...groupsSrc.matchAll(/(\w+): \{ label: "[^"]+", colour: "(#[0-9a-f]{6})"/g)].map((m) => [m[1], m[2]]));
const PEOPLE = "Data: Wikimedia pageviews + Wikidata";
const SITES = "Data: Tranco + Cloudflare Radar";
const MON = (m) => new Date(m + "-01").toLocaleString("en-GB", { month: "short" });
const LONG = (m) => new Date(m + "-01").toLocaleString("en-GB", { month: "long", year: "numeric" });
const fmt = (n) => n.toLocaleString("en-GB");
const worldMonths = ["01","02","03","04","05","06","07","08","09","10"].map((m) => `2026-${m}`);
const rankOf = (id, m) => snap(m, "world").sites.find((s) => s.id === id)?.rank ?? null;
const sq = (s, set, sub) => `<div class="sq" style="--u:120px;--set:${set}"><div class="band">${s.rank}</div><div class="body"><div class="tile">${(s.brand ?? s.name).replace(/[^A-Za-z0-9]/g, "").slice(0, 1)}</div><div class="brand">${s.brand ?? s.name}</div><div class="domain">${sub}</div></div></div>`;
const report = [];

const browser = await chromium.launch({ executablePath: findChrome() });
async function card(hash, name) {
  const p = await browser.newPage({ viewport: { width: 1280, height: 1100 }, deviceScaleFactor: 2, reducedMotion: "reduce" });
  await p.goto(`${SITE}/?r=${Date.now()}${hash}`);
  await p.waitForSelector("dialog.card[open]"); await p.waitForTimeout(1500);
  await p.evaluate(() => { document.activeElement?.blur(); return document.fonts.ready; });
  const path = resolve(tmp, `${name}.png`);
  await p.locator("dialog.card").screenshot({ path }); await p.close();
  return `out/${name}.png`;
}
async function post(file, html, credit) {
  const p = await browser.newPage({ viewport: { width: 1200, height: 675 } });
  await p.goto(pathToFileURL(resolve(here, "post.html")).href);
  await p.evaluate((a) => window.render(a), { html, credit });
  await p.evaluate(() => Promise.all([document.fonts.ready, ...[...document.images].map((i) => i.decode().catch(() => {}))]));
  await p.screenshot({ path: resolve(out, file) }); await p.close();
}
const W = (t) => `<div class="wordmark">Search<b>opoly</b></div>${t}`;
try {
  // 1. Football summer
  const fm = ["2026-05", "2026-06", "2026-07", "2026-08"];
  const counts = fm.map((m) => snap(m, "people").sites.filter((s) => s.category === "sport"));
  const top3 = snap("2026-07", "people").sites.slice(0, 3);
  report.push(`football: sport squares ${counts.map((c) => c.length).join(",")}; July top3 ${top3.map((s) => s.name).join(", ")}`);
  await post("football-summer.png", W(`<div class="text" style="width:1080px">
    <h1>A football summer on Wikipedia</h1><p class="sub">Sport squares on the Most viewed people board (of 28), May to August 2026</p>
    <div class="months">${fm.map((m, i) => `<div class="m"><div class="mini" style="--set:${COL.sport};grid-template-columns:repeat(7,16px)">${snap(m, "people").sites.map((s) => `<i class="${s.category === "sport" ? "on" : ""}"></i>`).join("")}</div><div class="n">${counts[i].length}</div><div class="l">${MON(m)}</div></div>`).join("")}
    <div class="m" style="margin-left:40px;text-align:left"><div class="l" style="margin-bottom:6px">July's top 3</div><div class="sqrow" style="margin-top:0">${top3.map((s) => sq({ ...s, name: s.name }, COL[s.category], fmt(s.views) + " views")).join("")}</div></div></div></div>`), PEOPLE);

  // 2. Haaland
  const hj = snap("2026-06", "people").sites.find((s) => s.id === "erling-haaland");
  const hl = snap("2026-07", "people").sites.find((s) => s.id === "erling-haaland");
  report.push(`haaland: Jun #${hj.rank} ${hj.views}, Jul #${hl.rank} ${hl.views}`);
  await post("haaland.png", W(`<div class="text" style="width:600px"><h1>Erling Haaland went from #${hj.rank} to #${hl.rank}</h1>
    <p class="sub">English Wikipedia page views, June vs July 2026</p>
    <div class="stats"><div class="stat"><div class="k">June</div><div class="v">#${hj.rank}</div><div>${fmt(hj.views)} views</div></div>
    <div class="stat hi"><div class="k">July</div><div class="v">#${hl.rank}</div><div>${fmt(hl.views)} views</div></div>
    <div class="stat"><div class="k">Change</div><div class="v">×${(hl.views / hj.views).toFixed(1)}</div><div>views</div></div></div></div>
    <div class="cards"><img src="${await card("#people/sport/2026-07/erling-haaland", "card-haaland")}"></div>`), PEOPLE);

  // 3. ChatGPT
  const cg = worldMonths.map((m) => [m, rankOf("chatgpt", m)]);
  report.push(`chatgpt: ${cg.map(([m, r]) => `${MON(m)} ${r ?? "-"}`).join(", ")}`);
  const first = cg.find(([, r]) => r); const best = cg.filter(([, r]) => r).reduce((a, b) => (b[1] < a[1] ? b : a));
  await post("chatgpt.png", W(`<div class="text" style="width:600px"><h1>ChatGPT on the world's top 28</h1>
    <p class="sub">Rank among the most visited sites, ${MON(worldMonths[0])}–${MON(worldMonths.at(-1))} 2026</p>
    <div class="stats"><div class="stat"><div class="k">New in ${MON(first[0])}</div><div class="v">#${first[1]}</div></div>
    <div class="stat hi"><div class="k">Peak · ${MON(best[0])}</div><div class="v">#${best[1]}</div></div>
    <div class="stat"><div class="k">${MON("2026-06")}</div><div class="v">#${rankOf("chatgpt", "2026-06")}</div></div>
    <div class="stat"><div class="k">Now · ${MON("2026-10")}</div><div class="v">#${rankOf("chatgpt", "2026-10")}</div></div></div></div>
    <div class="cards"><img src="${await card("#world/2026-10/chatgpt", "card-chatgpt")}"></div>`), SITES);

  // Optional: Mail.ru + Dzen
  const cats = snap("2026-10", "world_categories");
  const dzNews = cats.boards.news.sites.find((s) => s.id === "dzen")?.rank;
  report.push(`mailru-dzen: Mail.ru #${rankOf("mail-ru", "2026-10")}, Dzen #${rankOf("dzen", "2026-10")} world, Dzen #${dzNews} on News`);
  await post("mailru-dzen.png", W(`<div class="text" style="width:330px"><h1 style="font-size:38px">Two Russian giants in the world's top 10</h1>
    <p class="sub">October 2026: Mail.ru is #${rankOf("mail-ru", "2026-10")} worldwide, and Dzen is #${rankOf("dzen", "2026-10")} worldwide and <b>#${dzNews} on the News &amp; sport board</b>.</p></div>
    <div class="cards" style="right:40px;top:44px;gap:16px"><img style="height:520px" src="${await card("#world/2026-10/mail-ru", "card-mailru")}"><img style="height:520px" src="${await card("#world/news/2026-10/dzen", "card-dzen")}"></div>`), SITES);

  // Optional: Google streak
  const gs = worldMonths.map((m) => rankOf("google", m));
  report.push(`google: ${gs.join(",")}`);
  await post("google-streak.png", W(`<div class="text" style="width:600px"><h1>Google: #1 in ${gs.filter((r) => r === 1).length} of ${gs.length} months</h1>
    <p class="sub">The world's most visited site every month of 2026 so far</p>
    <div class="sqrow" style="flex-wrap:wrap;gap:8px">${worldMonths.map((m, i) => `<div class="stat ${gs[i] === 1 ? "hi" : ""}" style="min-width:100px;padding:8px 12px"><div class="k">${MON(m)}</div><div class="v" style="font-size:28px">#${gs[i]}</div></div>`).join("")}</div></div>
    <div class="cards"><img src="${await card("#world/2026-10/google", "card-google-post")}"></div>`), SITES);

  // Optional: Roblox
  const rb = worldMonths.map((m) => [m, rankOf("roblox", m)]);
  report.push(`roblox: ${rb.map(([m, r]) => `${MON(m)} ${r}`).join(", ")}`);
  await post("roblox.png", W(`<div class="text" style="width:600px"><h1>Roblox climbed the summer holidays</h1>
    <p class="sub">Rank among the world's most visited sites, 2026</p>
    <div class="stats"><div class="stat"><div class="k">April</div><div class="v">#${rankOf("roblox", "2026-04")}</div></div>
    <div class="stat hi"><div class="k">August</div><div class="v">#${rankOf("roblox", "2026-08")}</div></div>
    <div class="stat"><div class="k">Now · Oct</div><div class="v">#${rankOf("roblox", "2026-10")}</div></div></div></div>
    <div class="cards"><img src="${await card("#world/2026-10/roblox", "card-roblox")}"></div>`), SITES);

  // Optional: Shopping October top 5
  const shop = cats.boards.shopping.sites.slice(0, 5).map((s) => ({ ...s, ...cats.brands[s.id], rank: s.rank }));
  report.push(`shopping: ${shop.map((s) => s.brand).join(", ")}`);
  await post("shopping-oct.png", W(`<div class="text" style="width:1080px"><h1>The world's top shops, October 2026</h1>
    <p class="sub">Most visited sites on the Shopping board</p>
    <div class="sqrow" style="transform:scale(1.5);transform-origin:left top">${shop.map((s) => sq(s, COL.shopping, s.domain)).join("")}</div></div>`), SITES);
} finally { await browser.close(); }
console.log(report.join("\n"));
