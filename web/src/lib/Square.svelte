<script>
  import { groupOf } from "./groups.js";
  import { initials } from "./layout.js";

  let { site = null, side, slot = 0, selected = false, hot = false, badge = null, onOpen } = $props();
  const group = $derived(site ? groupOf(site.group) : null);
</script>

{#if site}
  <button
    type="button"
    class="square {side}"
    class:selected
    class:hot
    style:--set={group.colour}
    aria-label={`Number ${site.rank}: ${site.brand}, ${group.label}${badge ? `, ${badge.label}` : ""}. Open site card`}
    aria-haspopup="dialog"
    onclick={(e) => onOpen(site, e.currentTarget)}
  >
    <span class="band"><span class="rank">{site.rank}</span></span>
    <span class="body">
      {#if badge}<span class="badge {badge.tone}" aria-hidden="true">{badge.text}</span>{/if}
      <span class="tile" aria-hidden="true">{initials(site.brand)}</span>
      <span class="text">
        <span class="brand">{site.brand}</span>
        <span class="domain">{site.domain}</span>
      </span>
    </span>
  </button>
{:else}
  <div class="square {side} placeholder" style:--set="#c9c2b3" aria-hidden="true">
    <span class="band"><span class="rank">{slot + 1}</span></span>
    <span class="body">
      <span class="tile ghost">?</span>
      <span class="text"><span class="brand muted">Coming soon</span></span>
    </span>
  </div>
{/if}

<style>
  .square {
    position: relative;
    display: flex;
    width: 100%;
    height: 100%;
    background: var(--paper);
    overflow: hidden;
    min-width: 0;
    min-height: 0;
    border: 0;
    padding: 0;
    margin: 0;
    font: inherit;
    color: inherit;
    text-align: inherit;
    transition: background-color 120ms ease, box-shadow 120ms ease;
  }
  button.square { cursor: pointer; }
  button.square:hover {
    background: color-mix(in srgb, var(--set) 7%, #fff);
    box-shadow: inset 0 0 0 2px var(--set);
  }
  button.square:focus-visible { outline: 3px solid var(--accent); outline-offset: -3px; }
  button.square.selected {
    background: color-mix(in srgb, var(--set) 12%, #fff);
    box-shadow: inset 0 0 0 3px var(--set);
  }
  button.square.hot { box-shadow: inset 0 0 0 3px #2b8a3e; }
  button.square.hot::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    box-shadow: inset 0 0 0 3px #2b8a3e;
    animation: pulse 1.6s ease-out 3;
  }
  @keyframes pulse { 50% { box-shadow: inset 0 0 0 7px rgba(43, 138, 62, 0.35); } }
  @media (prefers-reduced-motion: reduce) { button.square.hot::after { animation: none; } }

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
    position: relative;
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    padding: calc(var(--u) * 0.08);
    gap: calc(var(--u) * 0.06);
  }
  .bottom .body, .top .body { flex-direction: column; justify-content: center; text-align: center; }
  .left .body, .right .body { flex-direction: row; }

  .badge {
    position: absolute;
    top: calc(var(--u) * 0.05);
    right: calc(var(--u) * 0.05);
    font-family: var(--display);
    font-weight: 700;
    font-size: calc(var(--u) * 0.1);
    line-height: 1;
    padding: 0.25em 0.4em;
    border-radius: 999px;
    color: #fff;
    letter-spacing: 0.02em;
  }
  .badge.up { background: #2b8a3e; }
  .badge.down { background: #c92a2a; }
  .badge.new { background: var(--accent); }

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
  .bottom .brand, .top .brand { font-size: calc(var(--u) * 0.13); }
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
