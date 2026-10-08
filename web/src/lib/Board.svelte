<script>
  import Square from "./Square.svelte";
  import Corner from "./Corner.svelte";
  import { BOARD_SQUARES, CORNERS, squarePosition } from "./layout.js";
  import { GROUPS } from "./groups.js";
  import { monthLabel, dayLabel } from "./format.js";

  let { snapshot = null, boardKey, boardInfo, latestMonth, onSelectBoard } = $props();

  const slots = Array.from({ length: BOARD_SQUARES }, (_, i) => i);
  const sites = $derived(snapshot?.sites ?? []);
  const counts = $derived(
    sites.reduce((acc, s) => ((acc[s.group] = (acc[s.group] ?? 0) + 1), acc), {})
  );
  const podium = $derived(sites.slice(0, 3));
</script>

<div class="board" role="img" aria-label="Searchopoly board of the most visited websites">
  {#each CORNERS as corner (corner.id)}
    <Corner {corner} />
  {/each}

  {#each slots as slot (slot)}
    <Square site={sites[slot] ?? null} position={squarePosition(slot)} {slot} />
  {/each}

  <section class="centre">
    <p class="kicker">The web's most visited sites</p>
    <h1>Search<span>opoly</span></h1>

    <div class="toggle" role="tablist" aria-label="Choose a board">
      {#each ["world", "uk"] as key}
        <button
          role="tab"
          aria-selected={boardKey === key}
          class:active={boardKey === key}
          onclick={() => onSelectBoard(key)}
        >
          {key === "world" ? "World" : "UK"}
          {#if key === "uk" && boardInfo?.uk?.status !== "ok"}<em>soon</em>{/if}
        </button>
      {/each}
    </div>

    {#if snapshot}
      <p class="month">{monthLabel(snapshot.month)}</p>
      <p class="sub">Top {sites.length} sites, ranked by visits</p>

      <ol class="podium">
        {#each podium as s}
          <li style:--set={GROUPS[s.group]?.colour}>
            <span class="pos">{s.rank}</span>
            <span class="name">{s.brand}</span>
          </li>
        {/each}
      </ol>
    {:else}
      <div class="soon">
        <p class="month">UK data coming soon</p>
        <p class="sub">
          The UK board needs country-level rankings from Cloudflare Radar. It'll appear here as
          soon as that data is connected.
        </p>
        <button class="link" onclick={() => onSelectBoard("world")}>See the World board →</button>
      </div>
    {/if}

    <ul class="legend" aria-label="Colour sets">
      {#each Object.entries(GROUPS) as [key, g]}
        <li style:--set={g.colour}>
          <span class="swatch"></span>
          <span>{g.label}</span>
          {#if snapshot}<span class="count">{counts[key] ?? 0}</span>{/if}
        </li>
      {/each}
    </ul>

    <p class="source">
      {#if snapshot?.source?.name === "Tranco"}
        Data: Tranco list <a href={snapshot.source.url} target="_blank" rel="noopener">{snapshot.source.list_id}</a>,
        {dayLabel(snapshot.source.window?.split(" to ")[0])} to {dayLabel(snapshot.source.list_date)}
      {:else if snapshot}
        Data: {snapshot.source.name}, {snapshot.source.list_date}
      {:else}
        Latest World data: {monthLabel(latestMonth)}
      {/if}
    </p>
  </section>
</div>

<style>
  .board {
    --corner: 1.6fr;
    --u: calc(var(--board) / 10.2);
    --band: calc(var(--u) * 0.24);
    width: var(--board);
    aspect-ratio: 1;
    display: grid;
    grid-template-columns: var(--corner) repeat(7, 1fr) var(--corner);
    grid-template-rows: var(--corner) repeat(7, 1fr) var(--corner);
    gap: 2px;
    padding: 2px;
    background: var(--line);
    border-radius: 6px;
    box-shadow:
      0 0 0 calc(var(--u) * 0.1) var(--frame),
      0 30px 80px -20px rgba(0, 0, 0, 0.6);
  }

  .centre {
    grid-row: 2 / 9;
    grid-column: 2 / 9;
    background:
      radial-gradient(circle at 1px 1px, rgba(16, 24, 40, 0.07) 1px, transparent 0) 0 0 / 14px 14px,
      var(--paper-deep);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: calc(var(--u) * 0.35);
    gap: calc(var(--u) * 0.1);
  }

  .kicker {
    margin: 0;
    font-size: calc(var(--u) * 0.11);
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-soft);
  }
  h1 {
    margin: 0;
    font-family: var(--display);
    font-weight: 700;
    font-size: calc(var(--u) * 0.86);
    line-height: 0.95;
    letter-spacing: -0.045em;
    color: var(--ink);
  }
  h1 span { color: var(--accent); }

  .toggle {
    display: inline-flex;
    padding: 4px;
    margin-top: calc(var(--u) * 0.08);
    border-radius: 999px;
    background: #e7dfcf;
  }
  .toggle button {
    font: inherit;
    font-weight: 650;
    font-size: calc(var(--u) * 0.13);
    border: 0;
    padding: calc(var(--u) * 0.05) calc(var(--u) * 0.22);
    border-radius: 999px;
    background: transparent;
    color: var(--ink-soft);
    cursor: pointer;
  }
  .toggle button.active { background: var(--ink); color: var(--paper); }
  .toggle em {
    font-style: normal;
    font-size: 0.7em;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-left: 0.35em;
    padding: 0.1em 0.45em;
    border-radius: 999px;
    background: var(--accent);
    color: #fff;
    vertical-align: 0.15em;
  }

  .month {
    margin: calc(var(--u) * 0.08) 0 0;
    font-family: var(--display);
    font-weight: 700;
    font-size: calc(var(--u) * 0.26);
    color: var(--ink);
  }
  .sub { margin: 0; font-size: calc(var(--u) * 0.12); color: var(--ink-soft); max-width: 40ch; }

  .podium {
    list-style: none;
    margin: calc(var(--u) * 0.12) 0;
    padding: 0;
    display: flex;
    gap: calc(var(--u) * 0.1);
  }
  .podium li {
    display: flex;
    align-items: center;
    gap: calc(var(--u) * 0.07);
    padding: calc(var(--u) * 0.05) calc(var(--u) * 0.14) calc(var(--u) * 0.05) calc(var(--u) * 0.05);
    background: var(--paper);
    border-radius: 999px;
    box-shadow: 0 1px 0 rgba(16, 24, 40, 0.08), inset 0 0 0 1px rgba(16, 24, 40, 0.08);
  }
  .podium .pos {
    width: calc(var(--u) * 0.26);
    height: calc(var(--u) * 0.26);
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: var(--set);
    color: #fff;
    font-family: var(--display);
    font-weight: 700;
    font-size: calc(var(--u) * 0.13);
  }
  .podium .name { font-weight: 650; font-size: calc(var(--u) * 0.14); color: var(--ink); }

  .soon { display: flex; flex-direction: column; align-items: center; gap: calc(var(--u) * 0.08); margin-bottom: calc(var(--u) * 0.1); }
  .link {
    font: inherit;
    font-weight: 650;
    font-size: calc(var(--u) * 0.12);
    border: 0;
    background: none;
    color: var(--accent);
    cursor: pointer;
    padding: 0;
  }

  .legend {
    list-style: none;
    margin: calc(var(--u) * 0.08) 0 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: calc(var(--u) * 0.06) calc(var(--u) * 0.3);
    text-align: left;
  }
  .legend li {
    display: flex;
    align-items: center;
    gap: calc(var(--u) * 0.07);
    font-size: calc(var(--u) * 0.115);
    color: var(--ink);
  }
  .swatch {
    width: calc(var(--u) * 0.2);
    height: calc(var(--u) * 0.12);
    border-radius: 3px;
    background: var(--set);
    flex: none;
  }
  .count {
    margin-left: auto;
    color: var(--ink-soft);
    font-variant-numeric: tabular-nums;
    padding-left: calc(var(--u) * 0.1);
  }

  .source {
    margin: calc(var(--u) * 0.12) 0 0;
    font-size: calc(var(--u) * 0.1);
    color: var(--ink-soft);
  }
  .source a { color: inherit; }
</style>
