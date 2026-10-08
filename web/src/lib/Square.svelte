<script>
  import { groupOf } from "./groups.js";
  import { initials } from "./layout.js";

  let { site = null, position, slot } = $props();
  const group = $derived(site ? groupOf(site.group) : null);
</script>

<div
  class="square {position.side}"
  class:placeholder={!site}
  style:grid-row={position.row}
  style:grid-column={position.col}
  style:--set={group?.colour ?? "#c9c2b3"}
  title={site ? `#${site.rank} ${site.brand} (${site.domain}) · ${group.label}` : "Coming soon"}
>
  <div class="band">
    <span class="rank">{site ? site.rank : slot + 1}</span>
  </div>
  <div class="body">
    {#if site}
      <span class="tile" aria-hidden="true">{initials(site.brand)}</span>
      <span class="text">
        <span class="brand">{site.brand}</span>
        <span class="domain">{site.domain}</span>
      </span>
    {:else}
      <span class="tile ghost" aria-hidden="true">?</span>
      <span class="text"><span class="brand muted">Coming soon</span></span>
    {/if}
  </div>
</div>

<style>
  .square {
    position: relative;
    display: flex;
    background: var(--paper);
    overflow: hidden;
    min-width: 0;
    min-height: 0;
  }
  .square.bottom { flex-direction: column; }
  .square.top { flex-direction: column-reverse; }
  .square.left { flex-direction: row-reverse; }
  .square.right { flex-direction: row; }

  .band {
    flex: 0 0 var(--band);
    background: var(--set);
    display: grid;
    place-items: center;
    color: #fff;
  }
  .rank {
    font-family: var(--display);
    font-weight: 700;
    font-size: calc(var(--u) * 0.15);
    letter-spacing: 0.02em;
    font-variant-numeric: tabular-nums;
  }

  .body {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    padding: calc(var(--u) * 0.08);
    gap: calc(var(--u) * 0.06);
  }
  .bottom .body, .top .body {
    flex-direction: column;
    justify-content: center;
    text-align: center;
  }
  .left .body, .right .body { flex-direction: row; }

  .tile {
    flex: none;
    width: calc(var(--u) * 0.36);
    height: calc(var(--u) * 0.36);
    border-radius: calc(var(--u) * 0.09);
    display: grid;
    place-items: center;
    font-family: var(--display);
    font-weight: 700;
    font-size: calc(var(--u) * 0.2);
    color: var(--set);
    background: color-mix(in srgb, var(--set) 14%, var(--paper));
    box-shadow: inset 0 0 0 1.5px color-mix(in srgb, var(--set) 35%, transparent);
  }
  .bottom .tile, .top .tile {
    width: calc(var(--u) * 0.44);
    height: calc(var(--u) * 0.44);
    font-size: calc(var(--u) * 0.24);
  }
  .bottom .brand, .top .brand { font-size: calc(var(--u) * 0.13); }
  .tile.ghost { color: #b3ab9a; background: #ece6d9; box-shadow: none; }

  .text { display: flex; flex-direction: column; min-width: 0; gap: 2px; }
  .brand {
    font-weight: 650;
    font-size: calc(var(--u) * 0.122);
    line-height: 1.15;
    color: var(--ink);
    overflow-wrap: anywhere;
    hyphens: auto;
  }
  .brand.muted { color: #a39b8a; font-weight: 500; }
  .domain {
    font-size: calc(var(--u) * 0.088);
    color: var(--ink-soft);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .placeholder .band { background: repeating-linear-gradient(45deg, #d8d1c2 0 6px, #cfc7b6 6px 12px); }
  .placeholder .rank { color: #8f8777; }
</style>
