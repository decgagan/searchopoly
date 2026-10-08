<script>
  import { scaleLinear, scalePoint } from "d3-scale";
  import { line, curveMonotoneX } from "d3-shape";
  import { monthLabel } from "./format.js";

  // history: [{ month, rank|null }], oldest first. Rank 1 is drawn at the top.
  let { history, size = 28, colour, brand } = $props();

  const W = 380, H = 84, PAD = { l: 26, r: 10, t: 10, b: 20 };
  const x = $derived(scalePoint(history.map((h) => h.month), [PAD.l, W - PAD.r]));
  const y = $derived(scaleLinear([1, size], [PAD.t, H - PAD.b]));
  const path = $derived(
    line()
      .defined((h) => h.rank != null)
      .x((h) => x(h.month))
      .y((h) => y(h.rank))
      .curve(curveMonotoneX)(history)
  );
  const onBoard = $derived(history.filter((h) => h.rank != null));
  const best = $derived(onBoard.length ? Math.min(...onBoard.map((h) => h.rank)) : null);
  const short = (m) => monthLabel(m).slice(0, 3);
  const description = $derived(
    history.map((h) => `${monthLabel(h.month)}: ${h.rank ? `#${h.rank}` : "not on board"}`).join("; ")
  );
</script>

<figure class="spark">
  <figcaption>
    <span>Rank over time</span>
    {#if best}<span class="best">Best: #{best}</span>{/if}
  </figcaption>
  <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${brand} rank by month. ${description}`}>
    {#each [1, 10, 20, size] as r}
      <line class="grid" x1={PAD.l} x2={W - PAD.r} y1={y(r)} y2={y(r)} />
      <text class="axis" x={PAD.l - 6} y={y(r) + 3.5} text-anchor="end">{r}</text>
    {/each}
    <path d={path} fill="none" stroke={colour} stroke-width="2.5" stroke-linecap="round" />
    {#each history as h, i}
      {#if h.rank != null}
        <circle cx={x(h.month)} cy={y(h.rank)} r={i === history.length - 1 ? 4.5 : 3} fill={i === history.length - 1 ? colour : "#fff"} stroke={colour} stroke-width="2" />
      {:else}
        <text class="off" x={x(h.month)} y={H - PAD.b - 2} text-anchor="middle">·</text>
      {/if}
      {#if i === 0 || i === history.length - 1 || history.length <= 6}
        <text class="axis" x={x(h.month)} y={H - 4} text-anchor="middle">{short(h.month)}</text>
      {/if}
    {/each}
  </svg>
</figure>

<style>
  .spark { margin: 16px 0 0; }
  figcaption {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ink-soft);
    margin-bottom: 4px;
  }
  .best { color: var(--ink); }
  svg { width: 100%; height: auto; display: block; background: #fff; border: 1px solid #e6dfd1; border-radius: 12px; }
  .grid { stroke: #efe9dd; stroke-width: 1; }
  .axis { font-size: 10px; fill: #8a8f9c; font-family: var(--body); }
  .off { font-size: 18px; fill: #c4bcac; }
</style>
