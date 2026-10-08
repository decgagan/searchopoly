<script>
  import { flip } from "svelte/animate";
  import { fade } from "svelte/transition";
  import { cubicInOut } from "svelte/easing";
  import CentrePanel from "./CentrePanel.svelte";
  import { groupOf } from "./groups.js";
  import { initials } from "./layout.js";
  import { badgeFor } from "./movement.js";
  import { motion } from "./motion.svelte.js";

  let { snapshot = null, selectedId = null, onOpen, categoryLabels = {}, ...panel } = $props();
  const sites = $derived(snapshot?.sites ?? []);
</script>

<div class="mobile">
  <CentrePanel {snapshot} {onOpen} mobile {...panel} />

  {#if snapshot}
    <div class="start" aria-hidden="true">
      <svg viewBox="0 0 48 48"><path d="M10 24h28m0 0L27 13m11 11L27 35" /></svg>
      <span><strong>Log On</strong> · every visit starts here</span>
    </div>
    <ol class="list" aria-label={`Top ${sites.length} sites`}>
      {#each sites as site (site.id)}
        {@const g = groupOf(site.group)}
        {@const badge = badgeFor(site, snapshot)}
        <li
          style:--set={g.colour}
          animate:flip={{ duration: motion.move, easing: cubicInOut }}
          in:fade={{ duration: motion.fade }}
          out:fade={{ duration: motion.reduced ? 0 : 120 }}
        >
          <button
            type="button"
            class:selected={site.id === selectedId}
            onclick={(e) => onOpen(site, e.currentTarget)}
            aria-haspopup="dialog"
          >
            <span class="band">{site.rank}</span>
            <span class="tile" aria-hidden="true">{initials(site.brand)}</span>
            <span class="text">
              <span class="brand">{site.brand}</span>
              <span class="meta">{site.domain} · {categoryLabels[site.category] ?? site.category}</span>
            </span>
            <span class="sr-only">{badge ? `, ${badge.label}` : ""}. Open site card</span>
            {#if badge}<span class="badge {badge.tone}" aria-hidden="true">{badge.text}</span>{/if}
            <svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
          </button>
        </li>
      {/each}
    </ol>
  {:else}
    <ol class="list ghost" aria-hidden="true">
      {#each Array(6) as _, i}
        <li><span class="band">{i + 1}</span><span class="tile">?</span><span class="brand muted">Coming soon</span></li>
      {/each}
    </ol>
  {/if}
</div>

<style>
  .mobile { width: min(100%, 520px); min-width: 0; padding: 0 12px; display: flex; flex-direction: column; gap: 14px; }
  .start {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #d0d5dd;
    font-size: 13px;
    padding: 4px 6px 0;
  }
  .start strong { color: var(--paper); font-family: var(--display); }
  .start svg { width: 22px; height: 22px; fill: none; stroke: var(--accent); stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }

  .list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
  .list button, .ghost li {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 14px 0 0;
    min-height: 64px;
    border: 0;
    border-radius: 12px;
    background: var(--paper);
    font: inherit;
    color: inherit;
    text-align: left;
    overflow: hidden;
    cursor: pointer;
    box-shadow: 0 1px 0 rgba(0, 0, 0, 0.2);
  }
  .list button:active { transform: scale(0.99); }
  .list button:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .list button.selected { box-shadow: 0 0 0 3px var(--set); }
  .band {
    align-self: stretch;
    flex: 0 0 44px;
    display: grid;
    place-items: center;
    background: var(--set);
    color: #fff;
    font-family: var(--display);
    font-weight: 700;
    font-size: 17px;
    font-variant-numeric: tabular-nums;
  }
  .tile {
    flex: none;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    display: grid;
    place-items: center;
    font-family: var(--display);
    font-weight: 700;
    font-size: 19px;
    color: var(--set);
    background: color-mix(in srgb, var(--set) 14%, var(--paper));
    box-shadow: inset 0 0 0 1.5px color-mix(in srgb, var(--set) 35%, transparent);
  }
  .text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .brand { font-weight: 650; font-size: 16px; color: var(--ink); }
  .meta { font-size: 12.5px; color: var(--ink-soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .badge {
    flex: none;
    font-family: var(--display);
    font-weight: 700;
    font-size: 12px;
    padding: 3px 7px;
    border-radius: 999px;
    color: #fff;
  }
  .badge.up { background: var(--up); }
  .badge.down { background: var(--down); }
  .badge.new { background: var(--accent-strong); }
  .chev { width: 18px; height: 18px; flex: none; fill: none; stroke: #b0a898; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }

  .ghost li { cursor: default; opacity: 0.7; }
  .ghost .band { background: repeating-linear-gradient(45deg, #d8d1c2 0 6px, #cfc7b6 6px 12px); color: #8f8777; }
  .ghost .tile { color: #b3ab9a; background: #ece6d9; box-shadow: none; }
  .muted { color: #a39b8a; font-weight: 500; }
</style>
