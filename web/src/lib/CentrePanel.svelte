<script>
  import { groupOf, groupsFor } from "./groups.js";
  import { monthLabel, dayLabel } from "./format.js";
  import { summarise } from "./movement.js";
  import MonthPicker from "./MonthPicker.svelte";

  let {
    snapshot = null, boardKey, boardInfo, latestMonth, onSelectBoard, onOpen, mobile = false,
    months = [], onSelectMonth,
    filters = [], filter = null, onSelectFilter = () => {}, onPrefetchFilters = () => {},
  } = $props();
  const filterLabel = $derived(snapshot?.filterLabel ?? null);

  const summary = $derived(summarise(snapshot));

  const sites = $derived(snapshot?.sites ?? []);
  const counts = $derived(
    sites.reduce((acc, s) => ((acc[s.group] = (acc[s.group] ?? 0) + 1), acc), {})
  );
  const podium = $derived(sites.slice(0, 3));
  const boardLabel = (key) => (key === "world" ? "World" : "UK");
  const people = $derived(boardKey === "people");
  const legendGroups = $derived(groupsFor(boardKey));
  // Sites boards: switching back from People goes to the World board.
  const modes = [
    { key: "sites", label: "Most visited sites", short: "Websites", board: "world" },
    { key: "people", label: "Most viewed people", short: "People", board: "people" },
  ];
  // People churn a lot month to month: name the first few, count the rest.
  const few = (list) =>
    list.length > 5 ? `${list.slice(0, 4).join(", ")} and ${list.length - 4} more` : list.join(", ");
</script>

<section class="centre" class:mobile aria-labelledby="board-title">
  <!-- Two kinds of board: websites (World, UK) and people (Wikipedia page views). -->
  <div class="modes" role="group" aria-label="What the board ranks">
    {#each modes as m (m.key)}
      <button
        type="button"
        aria-pressed={(m.key === "people") === people}
        class:active={(m.key === "people") === people}
        onclick={() => { if ((m.key === "people") !== people) onSelectBoard(m.board); }}
      >{mobile ? m.short : m.label}</button>
    {/each}
  </div>
  <h1 id="board-title">Search<span>opoly</span></h1>

  {#if people}
    <p class="toggle-note">On English Wikipedia</p>
  {:else}
  <div class="toggle" role="group" aria-label="Choose a board">
    {#each ["world", "uk"] as key}
      <button
        type="button"
        aria-pressed={boardKey === key}
        class:active={boardKey === key}
        onclick={() => onSelectBoard(key)}
      >
        {boardLabel(key)}
        {#if boardInfo?.[key]?.status !== "ok"}<em>soon</em>{/if}
      </button>
    {/each}
  </div>
  {/if}

  {#if snapshot}
    <p class="month" aria-live="polite">{monthLabel(snapshot.month)}</p>
    {#if months.length > 1}
      <MonthPicker {months} month={snapshot.month} onSelect={onSelectMonth} compact={mobile} />
    {/if}
    <p class="sub">
      {#if people && filterLabel}
        Top {sites.length} {sites.length === 1 ? "person" : "people"} in {filterLabel}, ranked by page views{#if snapshot.depth > 5000}<span class="depth"> · from the top {snapshot.depth.toLocaleString("en-GB")} articles</span>{/if}
      {:else if people}
        Top {sites.length} people, ranked by Wikipedia page views
      {:else if filterLabel}
        Top {sites.length} {filterLabel} sites{boardKey === "uk" ? " in the UK" : " worldwide"}, ranked by visits
      {:else}
        Top {sites.length} sites{boardKey === "uk" ? " in the UK" : " worldwide"}, ranked by visits
      {/if}
    </p>
    {#if snapshot.vacant && people}
      <p class="vacant">
        {snapshot.vacant} vacant lot{snapshot.vacant === 1 ? "" : "s"}: nobody else in {filterLabel} is in
        the month's top {(snapshot.depth ?? 0).toLocaleString("en-GB")} articles. <a href="#about">Why?</a>
      </p>
    {:else if snapshot.vacant}
      <p class="vacant">
        {snapshot.vacant} vacant lot{snapshot.vacant === 1 ? "" : "s"}: no other {filterLabel ? `${filterLabel} ` : "real "}site is in
        the top {snapshot.depth.toLocaleString("en-GB")} {boardKey === "uk" ? "UK " : ""}domains. <a href="#about">Why?</a>
      </p>
    {/if}

    <ol class="podium" aria-label="Top three">
      {#each podium as s (s.id)}
        <li style:--set={groupOf(s.group).colour}>
          <button type="button" onclick={(e) => onOpen(s, e.currentTarget)}>
            <span class="pos">{s.rank}</span>
            <span class="name">{s.brand}</span>
          </button>
        </li>
      {/each}
    </ol>
    <div class="movers" aria-label="This month's movement">
      {#if summary}
        {#if summary.climber}
          <button type="button" class="mover up" onclick={(e) => onOpen(summary.climber, e.currentTarget)}>
            <span class="tag">Biggest climber</span> ▲{summary.climber.movement} {summary.climber.brand}
          </button>
        {/if}
        {#if summary.faller}
          <button type="button" class="mover down" onclick={(e) => onOpen(summary.faller, e.currentTarget)}>
            <span class="tag">Biggest faller</span> ▼{-summary.faller.movement} {summary.faller.brand}
          </button>
        {/if}
        {#if summary.newcomers.length}
          <span class="mover new"><span class="tag">New</span> {few(summary.newcomers.map((s) => s.brand))}</span>
        {/if}
        {#if summary.dropped.length}
          <span class="mover out"><span class="tag">Dropped out</span> {few(summary.dropped.map((s) => s.brand))}</span>
        {/if}
        {#if !summary.climber && !summary.faller && !summary.newcomers.length}
          <span class="mover out">No change from last month</span>
        {/if}
      {:else}
        <span class="mover out">First month on record: movement starts next month</span>
      {/if}
    </div>
  {:else}
    <div class="soon" role="status">
      <p class="month">{boardLabel(boardKey)} data coming soon</p>
      <p class="sub">
        The UK board needs country-level rankings from Cloudflare Radar. It'll appear here as
        soon as that data is connected.
      </p>
      <button type="button" class="link" onclick={() => onSelectBoard("world")}>See the World board →</button>
    </div>
  {/if}

  {#if filters.length && snapshot}
    <!-- The colour-set legend doubles as the industry filter. -->
    <p class="filters-label" id="filters-label">{people ? "Filter by field" : "Filter by industry"}</p>
    <div
      class="filters"
      role="group"
      aria-labelledby="filters-label"
      onpointerenter={onPrefetchFilters}
      onfocusin={onPrefetchFilters}
    >
      <button
        type="button"
        class="chip all"
        aria-pressed={!filter}
        onclick={() => onSelectFilter(null)}
      >
        <span class="swatch all" aria-hidden="true"></span>
        <span class="label">{people ? "All people" : "All sites"}</span>
      </button>
      {#each filters as f (f.id)}
        <button
          type="button"
          class="chip"
          style:--set={f.colour}
          style:--swatch={f.colours ? `linear-gradient(90deg, ${f.colours.join(", ")})` : null}
          aria-pressed={filter === f.id}
          onclick={() => onSelectFilter(filter === f.id ? null : f.id)}
        >
          <span class="swatch" aria-hidden="true"></span>
          <span class="label">{f.label}</span>
          {#if !filter}<span class="count"><span class="sr-only">, </span>{(f.groups ?? [f.group]).reduce((n, g) => n + (counts[g] ?? 0), 0)}<span class="sr-only"> on this board</span></span>{/if}
        </button>
      {/each}
    </div>
  {:else}
    <ul class="legend" aria-label="Colour sets">
      {#each Object.entries(legendGroups) as [key, g]}
        <li style:--set={g.colour}>
          <span class="swatch" aria-hidden="true"></span>
          <span>{g.label}</span>
          {#if snapshot}<span class="count" aria-label={`${counts[key] ?? 0} sites`}>{counts[key] ?? 0}</span>{/if}
        </li>
      {/each}
    </ul>
  {/if}

  <p class="source">
    {#if snapshot?.source?.name === "Wikimedia Pageviews"}
      Data: <a href={snapshot.source.url} target="_blank" rel="noopener">Wikimedia page views</a>,
      English Wikipedia, {monthLabel(snapshot.month)}; descriptions from Wikidata (both CC0)
    {:else if snapshot?.source?.name === "Tranco"}
      Data: Tranco list <a href={snapshot.source.url} target="_blank" rel="noopener">{snapshot.source.list_id}</a>,
      {dayLabel(snapshot.source.window?.split(" to ")[0])} to {dayLabel(snapshot.source.list_date)}
    {:else if snapshot}
      Data: <a href={snapshot.source.url} target="_blank" rel="noopener">{snapshot.source.name}</a>
      top domains{snapshot.source.location === "GB" ? " for the UK" : ""}{snapshot.source.list_date ? `, ${dayLabel(snapshot.source.list_date)}` : ""}
      (CC BY-NC 4.0)
    {:else}
      Latest World data: {monthLabel(latestMonth)}
    {/if}
    · <a class="how" href="#about">How it's made</a>
  </p>
</section>

<style>
  .centre {
    --fs-kicker: calc(var(--u) * 0.11);
    --fs-h1: calc(var(--u) * 0.86);
    --fs-toggle: calc(var(--u) * 0.13);
    --fs-month: calc(var(--u) * 0.26);
    --fs-sub: calc(var(--u) * 0.12);
    --fs-pod: calc(var(--u) * 0.14);
    --fs-legend: calc(var(--u) * 0.115);
    --fs-source: calc(var(--u) * 0.1);
    --fs-picker: calc(var(--u) * 0.11);
    --fs-movers: calc(var(--u) * 0.105);
    --gap: calc(var(--u) * 0.085);
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
    gap: var(--gap);
  }
  .centre > * { max-width: 100%; }
  .centre.mobile {
    --fs-kicker: 11px;
    --fs-h1: clamp(40px, 13vw, 56px);
    --fs-toggle: 15px;
    --fs-month: 22px;
    --fs-sub: 14px;
    --fs-pod: 14px;
    --fs-legend: 12.5px;
    --fs-source: 12px;
    --fs-picker: 13px;
    --fs-movers: 12.5px;
    --gap: 10px;
    padding: 28px 16px 22px;
    border-radius: 18px;
    min-width: 0;
    width: 100%;
  }

  /* Sites / People: the kicker line doubles as the switch between the two kinds of board. */
  .modes {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.2em 1.4em;
    font-size: var(--fs-kicker);
  }
  .modes button {
    font: inherit;
    font-weight: 650;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-soft);
    background: none;
    border: 0;
    padding: 0.35em 0 0.3em;
    border-bottom: 2px solid transparent;
    cursor: pointer;
  }
  .modes button:hover:not(.active) { color: var(--ink); border-bottom-color: #c9c2b3; }
  .modes button.active { color: var(--ink); border-bottom-color: var(--accent); cursor: default; }
  .modes button:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
  .centre.mobile .modes { font-size: 11.5px; gap: 0.2em 1.1em; }
  .centre.mobile .modes button { padding: 0.7em 0 0.6em; }  /* bigger touch target */
  .toggle-note {
    margin: 0;
    font-size: var(--fs-toggle);
    color: var(--ink-soft);
    padding: 0.35em 0;
  }
  h1 {
    margin: 0;
    font-family: var(--display);
    font-weight: 700;
    font-size: var(--fs-h1);
    line-height: 0.95;
    letter-spacing: -0.045em;
    color: var(--ink);
  }
  h1 span { color: var(--accent); }

  .toggle {
    display: inline-flex;
    padding: 4px;
    margin-top: calc(var(--gap) * 0.8);
    border-radius: 999px;
    background: #e7dfcf;
  }
  .toggle button {
    font: inherit;
    font-weight: 650;
    font-size: var(--fs-toggle);
    border: 0;
    padding: 0.35em 1.5em;
    border-radius: 999px;
    background: transparent;
    color: #4f5668;
    cursor: pointer;
  }
  .toggle button:hover:not(.active) { color: var(--ink); }
  .toggle button:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .toggle button.active { background: var(--ink); color: var(--paper); }
  .toggle em {
    font-style: normal;
    font-size: 0.7em;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-left: 0.35em;
    padding: 0.1em 0.45em;
    border-radius: 999px;
    background: var(--accent-strong);
    color: #fff;
    vertical-align: 0.15em;
  }

  .month {
    margin: calc(var(--gap) * 0.8) 0 0;
    font-family: var(--display);
    font-weight: 700;
    font-size: var(--fs-month);
    color: var(--ink);
  }
  .sub { margin: 0; font-size: var(--fs-sub); color: var(--ink-soft); max-width: 40ch; line-height: 1.4; }

  .podium {
    list-style: none;
    margin: calc(var(--gap) * 0.5) 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--gap);
  }
  .podium button {
    font: inherit;
    border: 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5em;
    padding: 0.35em 1em 0.35em 0.35em;
    background: var(--paper);
    border-radius: 999px;
    font-size: var(--fs-pod);
    box-shadow: 0 1px 0 rgba(16, 24, 40, 0.08), inset 0 0 0 1px rgba(16, 24, 40, 0.08);
    transition: box-shadow 120ms ease, transform 120ms ease;
  }
  .podium button:hover { box-shadow: 0 0 0 2px var(--set); transform: translateY(-1px); }
  .podium button:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .podium .pos {
    width: 1.85em;
    height: 1.85em;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: var(--set);
    color: #fff;
    font-family: var(--display);
    font-weight: 700;
    font-size: 0.93em;
  }
  .podium .name { font-weight: 650; color: var(--ink); }

  .movers {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.45em;
    font-size: var(--fs-movers);
    max-width: 46em;
    margin-top: calc(var(--gap) * -0.3);
  }
  .mover {
    font: inherit;
    font-weight: 600;
    border: 0;
    border-radius: 8px;
    padding: 0.35em 0.7em;
    background: #ebe3d4;
    color: var(--ink);
    display: inline-flex;
    align-items: center;
    gap: 0.45em;
  }
  button.mover { cursor: pointer; }
  button.mover:hover { filter: brightness(0.96); }
  button.mover:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .mover .tag {
    font-size: 0.78em;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
  }
  .mover.up { background: #d3f0da; color: #1e6b31; }
  .mover.down { background: #fbdcdc; color: #9b1f1f; }
  .mover.new { background: #fde3d0; color: #a8430a; }
  .mover.out { color: var(--ink-soft); font-weight: 500; }

  .soon { display: flex; flex-direction: column; align-items: center; gap: var(--gap); margin-bottom: var(--gap); }
  .link {
    font: inherit;
    font-weight: 650;
    font-size: var(--fs-sub);
    border: 0;
    background: none;
    color: var(--accent);
    cursor: pointer;
    padding: 0;
  }

  .legend {
    list-style: none;
    margin: calc(var(--gap) * 0.8) 0 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5em 2.4em;
    text-align: left;
    font-size: var(--fs-legend);
  }
  .mobile .legend { gap: 0.6em 1em; width: 100%; }
  .mobile .swatch { width: 1em; }
  .mobile .count { padding-left: 0.4em; }
  .legend li { display: flex; align-items: center; gap: 0.6em; color: var(--ink); }
  .swatch { width: 1.7em; height: 1em; border-radius: 3px; background: var(--swatch, var(--set)); flex: none; }
  .count { margin-left: auto; color: var(--ink-soft); font-variant-numeric: tabular-nums; padding-left: 0.8em; }

  .vacant { margin: 0; font-size: var(--fs-movers); color: var(--ink-soft); max-width: 46ch; line-height: 1.4; }
  .vacant a { color: var(--accent-strong); font-weight: 650; }

  .filters-label {
    margin: calc(var(--gap) * 0.8) 0 calc(var(--gap) * -0.4);
    font-size: calc(var(--fs-legend) * 0.85);
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-soft);
  }
  .filters {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.4em;
    font-size: var(--fs-legend);
    width: 100%;
    max-width: 58em;
  }
  .chip {
    font: inherit;
    display: flex;
    align-items: center;
    gap: 0.55em;
    min-width: 0;
    padding: 0.45em 0.7em;
    border: 0;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.55);
    box-shadow: inset 0 0 0 1px rgba(16, 24, 40, 0.1);
    color: var(--ink);
    text-align: left;
    cursor: pointer;
    transition: background-color 120ms ease, box-shadow 120ms ease, color 120ms ease;
  }
  .chip .label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .chip:hover { background: var(--paper); box-shadow: inset 0 0 0 2px var(--set, var(--ink)); }
  .chip:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .chip[aria-pressed="true"] {
    background: var(--set, var(--ink));
    color: #fff;
    font-weight: 650;
    box-shadow: none;
  }
  .chip[aria-pressed="true"] .swatch { background: #fff; }
  .chip[aria-pressed="true"] .count { color: #fff; }
  .chip .swatch { width: 0.85em; height: 0.85em; border-radius: 50%; }
  .chip .swatch.all {
    background: conic-gradient(#3b5bdb 0 14.3%, #d6336c 0 28.6%, #7048e8 0 42.9%, #b25900 0 57.1%,
      #d42c2c 0 71.4%, #09845f 0 85.7%, #546170 0);
  }
  .chip.all[aria-pressed="true"] { --set: var(--ink); }
  .chip.all[aria-pressed="true"] .swatch.all { box-shadow: 0 0 0 1.5px #fff; }
  .chip .count { padding-left: 0.4em; }
  .mobile .filters { grid-template-columns: repeat(2, minmax(0, 1fr)); max-width: none; }
  .mobile .chip { padding: 0.6em 0.75em; }
  .mobile .chip.all { grid-column: auto; }
  @media (prefers-reduced-motion: reduce) { .chip { transition: none; } }

  .source { margin: var(--gap) 0 0; font-size: var(--fs-source); color: var(--ink-soft); }
  .source a { color: inherit; }
  .source a.how { color: var(--accent); font-weight: 650; text-decoration: none; }
  .source a.how:hover { text-decoration: underline; }
</style>
