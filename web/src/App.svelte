<script>
  import Board from "./lib/Board.svelte";
  import MobileList from "./lib/MobileList.svelte";
  import SiteCard from "./lib/SiteCard.svelte";
  import About from "./lib/About.svelte";
  import OgCard from "./lib/OgCard.svelte";
  import { parseHash, formatHash } from "./lib/router.js";
  import { filtersFor, filterOf, PEOPLE_GROUPS } from "./lib/groups.js";
  import { monthLabel, compactNumber } from "./lib/format.js";

  const DATA = `${import.meta.env.BASE_URL}data`;
  const MOBILE_QUERY = "(max-width: 700px)";

  let index = $state(null);
  // snapshots[board][month] -> snapshot JSON
  let snapshots = $state({});
  let error = $state(null);
  let ready = $state(false);
  // Category boards: categoryData[board][month] -> raw <board>_categories.json. Loaded on
  // first use (about 9 KB gzipped per month), then cached. Raw because it's never mutated.
  let categoryData = $state.raw({});
  const categoryLoads = {};

  // URL hash is the source of truth for which board and which card are showing.
  // Rewrites old or non-canonical hashes (e.g. #world/tech -> #world/search-tech) in place.
  function readHash() {
    const r = parseHash(location.hash);
    const canonical = formatHash(r);
    if (r.page === "board" && location.hash && canonical !== location.hash) {
      history.replaceState(null, "", canonical || location.pathname + location.search);
    }
    return r;
  }
  let route = $state(readHash());
  window.addEventListener("hashchange", () => (route = readHash()));

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

  const categoryMonths = (board) => index?.category_boards?.months?.[board] ?? [];

  function loadCategories(board) {
    if (!categoryMonths(board).length) return Promise.resolve();
    categoryLoads[board] ??= Promise.all(
      categoryMonths(board).map((m) =>
        getJSON(`snapshots/${m}/${board}_categories.json`).then((d) => [m, d]))
    ).then((pairs) => {
      categoryData = { ...categoryData, [board]: Object.fromEntries(pairs) };
    }).catch((e) => {
      delete categoryLoads[board];
      error = e.message;
    });
    return categoryLoads[board];
  }

  // People use the same board as sites: the name goes where the brand goes, the view count
  // where the domain goes, and the colour set comes from the Wikidata-based category.
  const person = (p) => ({ ...p, brand: p.name, domain: `${compactNumber(p.views)} views`, group: p.category, kind: "person" });
  const peopleSnaps = new WeakMap();
  function peopleSnapshot(raw) {
    if (!peopleSnaps.has(raw)) {
      peopleSnaps.set(raw, {
        ...raw,
        sites: raw.sites.map(person),
        dropped_out: raw.dropped_out.map((d) => ({ ...d, brand: d.name })),
      });
    }
    return peopleSnaps.get(raw);
  }

  // Turn one category board into the same shape as a normal snapshot, so the board, list,
  // card, badges and movers work unchanged.
  const hydrated = new Map();
  function categorySnapshot(raw, key) {
    const cacheKey = `${raw.board}/${raw.month}/${key}`;
    if (hydrated.has(cacheKey)) return hydrated.get(cacheKey);
    const b = raw.boards[key];
    if (!b) return null;
    const people = raw.board === "people";
    const brands = raw.brands;
    const snap = {
      board: raw.board,
      month: raw.month,
      source: raw.source,
      has_previous_month: raw.has_previous_month,
      filter: key,
      filterLabel: filterOf(key, raw.board)?.label ?? key,
      depth: raw.depth,
      vacant: b.vacant,
      coverage: b.coverage,
      sites: b.sites.map((s) => (people ? person({ id: s.id, ...brands[s.id], ...s }) : { ...brands[s.id], ...s })),
      dropped_out: people ? b.dropped_out.map((d) => ({ ...d, brand: d.name })) : b.dropped_out,
    };
    hydrated.set(cacheKey, snap);
    return snap;
  }

  function snapshotFor(board, filter, m) {
    if (!filter) {
      const raw = snapshots[board]?.[m] ?? null;
      return raw && board === "people" ? peopleSnapshot(raw) : raw;
    }
    const raw = categoryData[board]?.[m];
    return raw ? categorySnapshot(raw, filter) : null;
  }

  async function load() {
    try {
      index = await getJSON("latest.json");
      if (route.filter) await loadCategories(route.board); // deep link to a category board
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
      // Wait for the two web fonts too, so text doesn't reflow (layout shift) after first paint.
      const fonts = ['700 1em "Space Grotesk Variable"', '400 1em "Inter Variable"', '650 1em "Inter Variable"'];
      jobs.push(...fonts.map((f) => document.fonts.load(f).catch(() => {})));
      await Promise.all(jobs);
      ready = true;
    } catch (e) {
      error = e.message;
    }
  }
  load();

  const months = $derived(index?.boards?.[route.board]?.months ?? []);
  const latest = $derived(months.at(-1) ?? null);
  const month = $derived(route.month && months.includes(route.month) ? route.month : latest);
  const filtersReady = $derived(ready && categoryMonths(route.board).length > 0);
  // Ignore a filter the board doesn't have (e.g. #uk/shopping or #people/shopping).
  const filter = $derived(
    filtersReady && filterOf(route.filter, route.board) ? route.filter : null
  );
  const filterLoading = $derived(!!filter && !categoryData[route.board]);
  const snapshot = $derived(snapshotFor(route.board, filter, month));
  const rankHistory = $derived(
    site ? months.map((m) => ({
      month: m,
      rank: snapshotFor(route.board, filter, m)?.sites.find((s) => s.id === site.id)?.rank ?? null,
    })) : []
  );
  const site = $derived(snapshot?.sites.find((s) => s.id === route.site) ?? null);
  const categoryLabels = $derived(
    Object.fromEntries([
      ...(index?.categories ?? []).map((c) => [c.category, c.label]),
      ...Object.entries(PEOPLE_GROUPS).map(([k, g]) => [k, g.label]),
    ])
  );
  const world = $derived(snapshot?.board === "world" ? snapshot : snapshots.world?.[index?.boards?.world?.months?.at(-1)]);
  const ukReady = $derived(index?.boards?.uk?.status === "ok");

  const openSite = (s) => navigate({ site: s.id });
  const closeSite = () => navigate({ site: null });
  const selectBoard = (board) => navigate({ page: "board", board, filter: null, month: null, site: null });
  // Keep the open card if the site is on the new month's board too.
  const selectMonth = (m) => {
    const keep = route.site && snapshotFor(route.board, filter, m)?.sites.some((s) => s.id === route.site);
    navigate({ month: m === latest ? null : m, site: keep ? route.site : null });
  };
  // Switch colour set, staying on the same month. Data loads first, so the board never
  // blanks: it animates straight from the old ranking to the new one.
  async function selectFilter(key) {
    if (key) await loadCategories(route.board);
    navigate({ filter: key, site: null });
  }
  const prefetchFilters = () => loadCategories(route.board);
  // A hand-edited or shared #world/<set> URL loads its data on the way in.
  $effect(() => {
    if (filter && !categoryData[route.board]) loadCategories(route.board);
  });
  function step(delta) {
    const sites = snapshot.sites;
    const i = sites.findIndex((s) => s.id === route.site) + delta;
    if (i >= 0 && i < sites.length) navigate({ site: sites[i].id });
  }

  // Scroll to the top when switching between the board and the method page.
  $effect(() => {
    route.page;
    window.scrollTo(0, 0);
  });

  $effect(() => {
    const where = ({ uk: "UK", people: "People" }[route.board] ?? "World") + (snapshot?.filterLabel ? ` ${snapshot.filterLabel}` : "");
    const people = route.board === "people";
    document.title = route.page === "about"
      ? "How Searchopoly is made · Searchopoly"
      : people && site
      ? `${site.brand}: #${site.rank} on the ${where} board, ${monthLabel(snapshot.month)} · Searchopoly`
      : people && snapshot
      ? `${snapshot.filterLabel ? `${snapshot.filterLabel}: the` : "The"} most viewed people on Wikipedia, ${monthLabel(snapshot.month)} · Searchopoly`
      : site
      ? `${site.brand}: #${site.rank} on the ${where} board, ${monthLabel(snapshot.month)} · Searchopoly`
      : snapshot?.filterLabel
      ? `${snapshot.filterLabel}: the most visited sites, ${monthLabel(snapshot.month)} · Searchopoly`
      : "Searchopoly: the web's most visited sites, as a board";
  });
</script>

{#if route.page === "og" && world && ready}
  <OgCard snapshot={world} boardInfo={index.boards} />
{:else}
<main class:mobile class:page={route.page === "about"}>
  {#if error}
    <p class="error">Couldn't load the board data ({error}).</p>
  {:else if !ready || filterLoading}
    <p class="loading">Loading the board…</p>
  {:else if index && route.page === "about"}
    <About {index} {world} />
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
      filters: filtersReady ? filtersFor(route.board) : [],
      filter,
      onSelectFilter: selectFilter,
      onPrefetchFilters: prefetchFilters,
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

{#if site && route.page === "board"}
  {#key `${route.board}/${filter}`}
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

{#if ready || error}
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
  <p>
    People data:
    <a href="https://wikimedia.org/api/rest_v1/" target="_blank" rel="noopener">Wikimedia page views</a>
    for English Wikipedia and
    <a href="https://www.wikidata.org/" target="_blank" rel="noopener">Wikidata</a>
    (names, descriptions, occupations), both
    <a href="https://creativecommons.org/publicdomain/zero/1.0/" target="_blank" rel="noopener">CC0</a>.
    Links go to the person's Wikipedia article.
  </p>
  <p><a href="#about">How it's made: sources, method and known biases</a></p>
  <p class="small">
    Not affiliated with any board game publisher, or with Tranco, Cloudflare, the Wikimedia
    Foundation, or any site or person shown.
    Brand names belong to their owners. Code
    <a href="https://github.com/decgagan/searchopoly" target="_blank" rel="noopener">on GitHub</a> (MIT).
  </p>
</footer>
{/if}
{/if}

<style>
  main {
    min-height: calc(100vh - 160px);
    display: grid;
    place-items: center;
    padding: calc(var(--board) * 0.05) 0 calc(var(--board) * 0.04);
  }
  main.mobile { place-items: start center; padding: 14px 0 24px; min-height: 0; }
  main.page { place-items: start center; padding: 40px 0; }
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
