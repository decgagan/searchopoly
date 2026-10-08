<script>
  import Board from "./lib/Board.svelte";

  const DATA = `${import.meta.env.BASE_URL}data`;

  let index = $state(null);
  const fromHash = () => (location.hash === "#uk" ? "uk" : "world");
  let boardKey = $state(fromHash());
  window.addEventListener("hashchange", () => (boardKey = fromHash()));

  function selectBoard(key) {
    boardKey = key;
    history.replaceState(null, "", key === "uk" ? "#uk" : location.pathname);
  }
  let snapshots = $state({});
  let error = $state(null);

  async function getJSON(path) {
    const res = await fetch(`${DATA}/${path}`);
    if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
    return res.json();
  }

  async function load() {
    try {
      index = await getJSON("latest.json");
      for (const [key, info] of Object.entries(index.boards)) {
        if (info.status === "ok" && info.latest) snapshots[key] = await getJSON(info.latest);
      }
    } catch (e) {
      error = e.message;
    }
  }
  load();

  const world = $derived(snapshots.world);
</script>

<main>
  {#if error}
    <p class="error">Couldn't load the board data ({error}).</p>
  {:else if index}
    <Board
      snapshot={snapshots[boardKey] ?? null}
      {boardKey}
      boardInfo={index.boards}
      latestMonth={index.latest_month}
      onSelectBoard={selectBoard}
    />
  {:else}
    <p class="loading">Loading the board…</p>
  {/if}
</main>

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
    UK data (coming soon):
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
