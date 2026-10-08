<script>
  import Board from "./lib/Board.svelte";
  import MobileList from "./lib/MobileList.svelte";
  import SiteCard from "./lib/SiteCard.svelte";
  import { parseHash, formatHash } from "./lib/router.js";

  const DATA = `${import.meta.env.BASE_URL}data`;
  const MOBILE_QUERY = "(max-width: 700px)";

  let index = $state(null);
  // snapshots[board][month] -> snapshot JSON
  let snapshots = $state({});
  let error = $state(null);

  // URL hash is the source of truth for which board and which card are showing.
  let route = $state(parseHash(location.hash));
  window.addEventListener("hashchange", () => (route = parseHash(location.hash)));

  function navigate(next) {
    route = { ...route, ...next };
    const hash = formatHash(route);
    history.replaceState(null, "", hash || location.pathname + location.search);
  }

  const media = matchMedia(MOBILE_QUERY);
  let mobile = $state(media.matches);
  media.addEventListener("change", (e) => (mobile = e.matches));

  async function getJSON(path) {
    const res = await fetch(`${DATA}/${path}`);
    if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
    return res.json();
  }

  async function load() {
    try {
      index = await getJSON("latest.json");
      // Every month of every live board is loaded up front (a few KB each), so the month
      // slider is instant. The UK board lights up as soon as uk.json exists.
      const jobs = [];
      for (const [key, info] of Object.entries(index.boards)) {
        if (info.status !== "ok") continue;
        snapshots[key] = {};
        for (const m of info.months) {
          jobs.push(getJSON(`snapshots/${m}/${key}.json`).then((d) => (snapshots[key][m] = d)));
        }
      }
      await Promise.all(jobs);
    } catch (e) {
      error = e.message;
    }
  }
  load();

  const months = $derived(index?.boards?.[route.board]?.months ?? []);
  const latest = $derived(months.at(-1) ?? null);
  const month = $derived(route.month && months.includes(route.month) ? route.month : latest);
  const snapshot = $derived(snapshots[route.board]?.[month] ?? null);
  const rankHistory = $derived(
    site ? months.map((m) => ({
      month: m,
      rank: snapshots[route.board]?.[m]?.sites.find((s) => s.id === site.id)?.rank ?? null,
    })) : []
  );
  const site = $derived(snapshot?.sites.find((s) => s.id === route.site) ?? null);
  const categoryLabels = $derived(
    Object.fromEntries((index?.categories ?? []).map((c) => [c.category, c.label]))
  );
  const world = $derived(snapshot?.board === "world" ? snapshot : snapshots.world?.[index?.boards?.world?.months?.at(-1)]);
  const ukReady = $derived(index?.boards?.uk?.status === "ok");

  const openSite = (s) => navigate({ site: s.id });
  const closeSite = () => navigate({ site: null });
  const selectBoard = (board) => navigate({ board, month: null, site: null });
  // Keep the open card if the site is on the new month's board too.
  const selectMonth = (m) => {
    const keep = route.site && snapshots[route.board]?.[m]?.sites.some((s) => s.id === route.site);
    navigate({ month: m === latest ? null : m, site: keep ? route.site : null });
  };
  function step(delta) {
    const sites = snapshot.sites;
    const i = sites.findIndex((s) => s.id === route.site) + delta;
    if (i >= 0 && i < sites.length) navigate({ site: sites[i].id });
  }

  $effect(() => {
    const where = route.board === "uk" ? "UK" : "World";
    document.title = site
      ? `${site.brand}: #${site.rank} on the ${where} board, ${snapshot.month} · Searchopoly`
      : "Searchopoly: the web's most visited sites, as a board";
  });
</script>

<main class:mobile>
  {#if error}
    <p class="error">Couldn't load the board data ({error}).</p>
  {:else if index}
    {@const props = {
      snapshot,
      boardKey: route.board,
      boardInfo: index.boards,
      latestMonth: index.latest_month,
      onSelectBoard: selectBoard,
      onOpen: openSite,
      selectedId: site?.id ?? null,
      months,
      onSelectMonth: selectMonth,
    }}
    {#if mobile}
      <MobileList {...props} {categoryLabels} />
    {:else}
      <Board {...props} />
    {/if}
  {:else}
    <p class="loading">Loading the board…</p>
  {/if}
</main>

{#if site}
  {#key route.board}
    <SiteCard
      {site}
      {snapshot}
      boardKey={route.board}
      {categoryLabels}
      history={rankHistory}
      onClose={closeSite}
      onStep={step}
    />
  {/key}
{/if}

<footer>
  <p>
    <strong>Searchopoly</strong> ranks websites by relative popularity of visits, not search volume.
    Infrastructure domains (CDNs, ad servers, telemetry) are removed and sibling domains merged into brands.
  </p>
  <p>
    World data:
    <a href="https://tranco-list.eu" target="_blank" rel="noopener">Tranco</a>{#if world?.source?.list_id}{" "}list
      <a href={world.source.url} target="_blank" rel="noopener">{world.source.list_id}</a>{/if}
    (Le Pochat et al., NDSS 2019,
    <a href="https://doi.org/10.14722/ndss.2019.23386" target="_blank" rel="noopener">doi:10.14722/ndss.2019.23386</a>).
    UK data{ukReady ? "" : " (coming soon)"}:
    <a href="https://radar.cloudflare.com/domains" target="_blank" rel="noopener">Cloudflare Radar</a>, licensed
    <a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank" rel="noopener">CC BY-NC 4.0</a>.
    Tranco also includes Radar data. Data modified as described above.
  </p>
  <p class="small">
    Not affiliated with any board game publisher, or with Tranco, Cloudflare or any site shown.
    Brand names belong to their owners. Code
    <a href="https://github.com/decgagan/searchopoly" target="_blank" rel="noopener">on GitHub</a> (MIT).
  </p>
</footer>

<style>
  main {
    min-height: calc(100vh - 160px);
    display: grid;
    place-items: center;
    padding: calc(var(--board) * 0.05) 0 calc(var(--board) * 0.04);
  }
  main.mobile { place-items: start center; padding: 14px 0 24px; min-height: 0; }
  .loading, .error { color: var(--paper); opacity: 0.8; }
  footer {
    max-width: 880px;
    margin: 0 auto;
    padding: 0 24px 40px;
    color: #98a2b3;
    font-size: 13px;
    line-height: 1.6;
    text-align: center;
  }
  footer p { margin: 0 0 8px; }
  footer strong { color: var(--paper); }
  footer a { color: #d0d5dd; }
  footer .small { font-size: 12px; color: #7a8599; }
</style>
