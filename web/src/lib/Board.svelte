<script>
  import Square from "./Square.svelte";
  import Corner from "./Corner.svelte";
  import CentrePanel from "./CentrePanel.svelte";
  import { BOARD_SQUARES, CORNERS, squarePosition } from "./layout.js";

  let { snapshot = null, selectedId = null, onOpen, ...panel } = $props();

  const slots = Array.from({ length: BOARD_SQUARES }, (_, i) => i);
  const sites = $derived(snapshot?.sites ?? []);
</script>

<div class="board">
  {#each CORNERS as corner (corner.id)}
    <Corner {corner} />
  {/each}

  {#each slots as slot (slot)}
    <Square
      site={sites[slot] ?? null}
      position={squarePosition(slot)}
      {slot}
      selected={sites[slot]?.id === selectedId}
      {onOpen}
    />
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
</style>
