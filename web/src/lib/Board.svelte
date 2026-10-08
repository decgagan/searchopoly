<script>
  import { flip } from "svelte/animate";
  import { fade } from "svelte/transition";
  import { cubicInOut } from "svelte/easing";
  import Square from "./Square.svelte";
  import Corner from "./Corner.svelte";
  import CentrePanel from "./CentrePanel.svelte";
  import { BOARD_SQUARES, CORNERS, squarePosition } from "./layout.js";
  import { badgeFor, summarise } from "./movement.js";
  import { motion } from "./motion.svelte.js";

  let { snapshot = null, selectedId = null, onOpen, ...panel } = $props();

  const sites = $derived(snapshot?.sites ?? []);
  const empty = $derived(
    Array.from({ length: Math.max(0, BOARD_SQUARES - sites.length) }, (_, i) => sites.length + i)
  );
  const hotId = $derived(summarise(snapshot)?.climber?.id ?? null);
</script>

<div class="board">
  {#each CORNERS as corner (corner.id)}
    <Corner {corner} />
  {/each}

  <!-- Keyed by site: when the month changes, each site glides to its new square (FLIP). -->
  {#each sites as site, i (site.id)}
    {@const pos = squarePosition(i)}
    <div
      class="cell"
      style:grid-row={pos.row}
      style:grid-column={pos.col}
      animate:flip={{ duration: motion.move, easing: cubicInOut }}
      in:fade={{ duration: motion.fade, delay: motion.fade }}
      out:fade={{ duration: motion.fade }}
    >
      <Square
        {site}
        side={pos.side}
        selected={site.id === selectedId}
        hot={site.id === hotId}
        badge={badgeFor(site, snapshot)}
        {onOpen}
      />
    </div>
  {/each}

  {#each empty as slot (slot)}
    {@const pos = squarePosition(slot)}
    <div class="cell" style:grid-row={pos.row} style:grid-column={pos.col}>
      <Square side={pos.side} {slot} />
    </div>
  {/each}

  <CentrePanel {snapshot} {onOpen} {...panel} />
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
  .cell { min-width: 0; min-height: 0; display: flex; position: relative; }
  .cell:hover, .cell:focus-within { z-index: 3; }
</style>
