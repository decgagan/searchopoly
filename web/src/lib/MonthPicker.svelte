<script>
  import { onDestroy } from "svelte";
  import { monthLabel } from "./format.js";
  import { motion } from "./motion.svelte.js";

  let { months, month, onSelect, compact = false } = $props();

  const index = $derived(Math.max(0, months.indexOf(month)));
  const short = (m) => {
    const [y, mm] = m.split("-").map(Number);
    const label = new Date(Date.UTC(y, mm - 1, 1)).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
    return mm === 1 || m === months[0] ? `${label} ’${String(y).slice(2)}` : label;
  };

  let timer = $state(null);
  const playing = $derived(timer !== null);

  function go(i) {
    if (i >= 0 && i < months.length) onSelect(months[i]);
  }
  function stop() {
    clearInterval(timer);
    timer = null;
  }
  function togglePlay() {
    if (playing) return stop();
    if (index === months.length - 1) go(0);
    timer = setInterval(() => {
      const next = months.indexOf(month) + 1;
      if (next >= months.length) stop();
      else go(next);
    }, motion.reduced ? 1200 : 1500);
  }
  onDestroy(stop);
</script>

<div class="picker" class:compact role="group" aria-label="Choose a month">
  <button type="button" class="step" onclick={() => { stop(); go(index - 1); }} disabled={index === 0} aria-label="Previous month">‹</button>
  <div class="track">
    <input
      type="range"
      min="0"
      max={months.length - 1}
      step="1"
      value={index}
      oninput={(e) => { stop(); go(Number(e.currentTarget.value)); }}
      aria-label="Month"
      aria-valuetext={monthLabel(month)}
      style:--pct={`${(index / Math.max(1, months.length - 1)) * 100}%`}
    />
    <div class="ticks" aria-hidden="true">
      {#each months as m, i}
        <span class:active={i === index} style:left={`${(i / Math.max(1, months.length - 1)) * 100}%`}>{short(m)}</span>
      {/each}
    </div>
  </div>
  <button type="button" class="step" onclick={() => { stop(); go(index + 1); }} disabled={index === months.length - 1} aria-label="Next month">›</button>
  <button type="button" class="play" onclick={togglePlay} aria-pressed={playing} aria-label={playing ? "Pause" : "Play through the months"}>
    {#if playing}
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14M16 5v14" /></svg>
    {:else}
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5l11 7-11 7z" /></svg>
    {/if}
  </button>
</div>

<style>
  .picker {
    --fs: var(--fs-picker, 12px);
    display: flex;
    align-items: center;
    gap: 0.6em;
    width: min(100%, 34em);
    font-size: var(--fs);
    margin-top: 0.3em;
  }
  .track { position: relative; flex: 1; padding-bottom: 1.5em; }
  input[type="range"] {
    width: 100%;
    margin: 0;
    appearance: none;
    background: transparent;
    height: 1.6em;
    cursor: pointer;
  }
  input[type="range"]::-webkit-slider-runnable-track {
    height: 0.45em;
    border-radius: 999px;
    background: linear-gradient(to right, var(--accent) var(--pct), #ddd4c3 var(--pct));
  }
  input[type="range"]::-moz-range-track { height: 0.45em; border-radius: 999px; background: #ddd4c3; }
  input[type="range"]::-moz-range-progress { height: 0.45em; border-radius: 999px; background: var(--accent); }
  input[type="range"]::-webkit-slider-thumb {
    appearance: none;
    width: 1.4em;
    height: 1.4em;
    margin-top: -0.48em;
    border-radius: 50%;
    background: var(--ink);
    border: 3px solid var(--paper);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  }
  input[type="range"]::-moz-range-thumb {
    width: 1.1em;
    height: 1.1em;
    border-radius: 50%;
    background: var(--ink);
    border: 3px solid var(--paper);
  }
  input[type="range"]:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; border-radius: 999px; }
  .ticks { position: absolute; left: 0.7em; right: 0.7em; bottom: 0; height: 1.2em; }
  .ticks span {
    position: absolute;
    transform: translateX(-50%);
    font-size: 0.82em;
    color: var(--ink-soft);
    white-space: nowrap;
  }
  .ticks span.active { color: var(--ink); font-weight: 700; }
  .compact .ticks span:not(.active):not(:first-child):not(:last-child) { visibility: hidden; }

  .step, .play {
    flex: none;
    width: 2.3em;
    height: 2.3em;
    margin-bottom: 1.5em;
    border-radius: 50%;
    border: 1px solid #d6cdbb;
    background: var(--paper);
    color: var(--ink);
    font-size: 1em;
    line-height: 1;
    cursor: pointer;
    display: grid;
    place-items: center;
  }
  .step { font-size: 1.3em; width: 1.75em; height: 1.75em; margin-bottom: 1.15em; }
  .play { background: var(--ink); color: var(--paper); border-color: var(--ink); }
  .play svg { width: 1.1em; height: 1.1em; fill: currentColor; stroke: currentColor; stroke-width: 2; stroke-linejoin: round; }
  .step:disabled { opacity: 0.35; cursor: default; }
  .step:focus-visible, .play:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
</style>
