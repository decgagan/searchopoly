<script>
  // 1200x630 share image, rendered at #og and captured by scripts/og-image.mjs.
  import Board from "./Board.svelte";
  import { groupOf } from "./groups.js";
  import { monthLabel } from "./format.js";

  let { snapshot, boardInfo = {} } = $props();
  const top = $derived(snapshot.sites.slice(0, 5));
</script>

<div class="og" data-og-ready>
  <div class="copy">
    <p class="kicker">The web's most visited sites</p>
    <h1>Search<span>opoly</span></h1>
    <p class="month">{monthLabel(snapshot.month)} · World</p>
    <ol>
      {#each top as s (s.id)}
        <li style:--set={groupOf(s.group).colour}><b>{s.rank}</b>{s.brand}</li>
      {/each}
    </ol>
    <p class="url">searchopoly.co.uk</p>
  </div>
  <div class="board-wrap" aria-hidden="true">
    <Board {snapshot} boardKey="world" {boardInfo} months={[]} onOpen={() => {}} onSelectBoard={() => {}} onSelectMonth={() => {}} />
  </div>
</div>

<style>
  .og {
    width: 1200px;
    height: 630px;
    display: flex;
    align-items: center;
    gap: 40px;
    padding: 0 40px 0 64px;
    background:
      radial-gradient(900px 500px at 75% 10%, #22304a 0%, transparent 70%),
      #101828;
    overflow: hidden;
  }
  .copy { flex: 1; color: var(--paper); }
  .kicker {
    margin: 0 0 10px;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #98a2b3;
  }
  h1 {
    margin: 0;
    font-family: var(--display);
    font-size: 92px;
    line-height: 0.95;
    letter-spacing: -0.045em;
  }
  h1 span { color: var(--accent); }
  .month { margin: 18px 0 22px; font-family: var(--display); font-size: 28px; font-weight: 700; }
  ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  li { display: flex; align-items: center; gap: 14px; font-size: 24px; font-weight: 650; }
  li b {
    width: 38px;
    height: 38px;
    border-radius: 9px;
    background: var(--set);
    display: grid;
    place-items: center;
    font-family: var(--display);
    font-size: 20px;
  }
  .url { margin: 26px 0 0; font-size: 20px; color: #d0d5dd; font-weight: 600; }
  .board-wrap { --board: 540px; pointer-events: none; flex: none; }
</style>
