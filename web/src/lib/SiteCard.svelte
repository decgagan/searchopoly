<script>
  import { tick } from "svelte";
  import { groupOf } from "./groups.js";
  import { initials } from "./layout.js";
  import { describeMovement } from "./movement.js";
  import Sparkline from "./Sparkline.svelte";

  let { site, snapshot, boardKey, categoryLabels = {}, history = [], onClose, onStep } = $props();

  let dialog;
  let closeBtn;
  let opener = null;

  const group = $derived(groupOf(site.group));
  const move = $derived(describeMovement(site, snapshot));
  const total = $derived(snapshot.sites.length);
  const sourceName = $derived(snapshot.source?.name ?? site.source);
  const boardName = $derived(boardKey === "uk" ? "UK" : "World");
  const href = $derived(`https://${site.domain}`);

  // Open as a modal: the rest of the page becomes inert and Esc fires "cancel".
  $effect(() => {
    if (!dialog.open) {
      opener = document.activeElement;
      dialog.showModal();
    }
    return () => {
      if (dialog?.open) dialog.close();
    };
  });

  // Move focus to the close button whenever the card's site changes.
  $effect(() => {
    site.id;
    tick().then(() => closeBtn?.focus());
  });

  function close() {
    onClose();
    // Give focus back to whatever opened the card.
    tick().then(() => opener?.isConnected && opener.focus());
  }

  function onKeydown(e) {
    if (e.key === "ArrowRight") { e.preventDefault(); onStep(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); onStep(-1); }
    else if (e.key === "Tab") {
      // Keep Tab cycling inside the card.
      const items = [...dialog.querySelectorAll("a[href], button:not([disabled])")];
      const first = items[0], last = items.at(-1);
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }
</script>

<dialog
  bind:this={dialog}
  class="card"
  style:--set={group.colour}
  aria-labelledby="card-title"
  aria-describedby="card-summary"
  oncancel={(e) => { e.preventDefault(); close(); }}
  onclick={(e) => { if (e.target === dialog) close(); }}
  onkeydown={onKeydown}
>
  <div class="sheet">
    <header>
      <span class="watermark" aria-hidden="true">{initials(site.brand)}</span>
      <div class="top">
        <span class="set">{group.label}</span>
        <button bind:this={closeBtn} type="button" class="close" onclick={close} aria-label="Close site card">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
        </button>
      </div>
      <p class="rank"><span>#{site.rank}</span> of {total} · {boardName}</p>
      <h2 id="card-title">{site.brand}</h2>
      <p class="domain">{site.domain}</p>
    </header>

    <div class="content">
      <p id="card-summary" class="sr-only">
        {site.brand} is number {site.rank} on the {boardName} board for this month. {move.label}.
      </p>

      <dl class="stats">
        <div>
          <dt>This month</dt>
          <dd class="big">#{site.rank}</dd>
        </div>
        <div>
          <dt>Last month</dt>
          <dd class="big">{site.previous_rank ? `#${site.previous_rank}` : "—"}</dd>
        </div>
        <div class="move {move.tone}">
          <dt>Movement</dt>
          <dd><span class="sym" aria-hidden="true">{move.symbol}</span> {move.label}</dd>
          <dd class="detail">{move.detail}</dd>
        </div>
      </dl>

      {#if history.length > 1}
        <Sparkline {history} size={total} colour={group.colour} brand={site.brand} />
      {/if}

      <dl class="facts">
        <div><dt>Category</dt><dd>{categoryLabels[site.category] ?? site.category}</dd></div>
        <div><dt>Raw rank</dt><dd>#{site.source_rank} in {sourceName}{snapshot.source?.list_id ? ` list ${snapshot.source.list_id}` : ""}</dd></div>
        {#if site.merged_domains?.length > 1}
          <div class="domains">
            <dt>Domains counted</dt>
            <dd>
              {#each site.merged_domains as d}<span class="chip">{d}</span>{/each}
            </dd>
          </div>
        {/if}
      </dl>

      {#if site.note}
        <aside class="note">
          <p class="note-title">About this rank</p>
          <p>{site.note}</p>
        </aside>
      {/if}
    </div>

    <footer>
      <a class="visit" {href} target="_blank" rel="noopener noreferrer">
        Visit {site.domain}
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8" /></svg>
      </a>
      <div class="steps">
        <button type="button" onclick={() => onStep(-1)} disabled={site.rank === 1} aria-label="Previous site">‹</button>
        <button type="button" onclick={() => onStep(1)} disabled={site.rank === total} aria-label="Next site">›</button>
      </div>
    </footer>
  </div>
</dialog>

<style>
  .card {
    padding: 0;
    border: 0;
    background: transparent;
    width: min(440px, calc(100vw - 32px));
    max-height: calc(100vh - 32px);
    overflow: visible;
    color: var(--ink);
  }
  .card::backdrop {
    background: rgba(10, 15, 28, 0.62);
    backdrop-filter: blur(3px);
  }
  .card[open] { animation: pop 160ms ease-out; }
  @keyframes pop { from { opacity: 0; transform: translateY(8px) scale(0.98); } }

  .sheet {
    background: var(--paper);
    border-radius: 18px;
    overflow: hidden auto;
    max-height: calc(100vh - 32px);
    box-shadow: 0 30px 80px -10px rgba(0, 0, 0, 0.55), 0 0 0 6px var(--frame);
  }

  header {
    position: relative;
    overflow: hidden;
    background: var(--set);
    color: #fff;
    padding: 18px 22px 22px;
  }
  .watermark {
    position: absolute;
    right: -6px;
    bottom: -38px;
    font-family: var(--display);
    font-weight: 700;
    font-size: 170px;
    line-height: 1;
    color: rgba(255, 255, 255, 0.14);
    pointer-events: none;
  }
  .top { display: flex; align-items: center; justify-content: space-between; }
  .set {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    background: rgba(255, 255, 255, 0.18);
    padding: 4px 10px;
    border-radius: 999px;
  }
  .close {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    border: 0;
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
    cursor: pointer;
    display: grid;
    place-items: center;
  }
  .close:hover { background: rgba(255, 255, 255, 0.3); }
  .close svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; }
  .close:focus-visible, .steps button:focus-visible, .visit:focus-visible { outline: 3px solid var(--ink); outline-offset: 2px; }

  .rank { margin: 18px 0 2px; font-size: 14px; font-weight: 600; opacity: 0.92; }
  .rank span { font-family: var(--display); font-weight: 700; font-size: 18px; }
  h2 {
    margin: 0;
    font-family: var(--display);
    font-weight: 700;
    font-size: 40px;
    line-height: 1;
    letter-spacing: -0.03em;
    position: relative;
  }
  .domain { margin: 6px 0 0; font-size: 15px; opacity: 0.9; position: relative; }

  .content { padding: 18px 22px 4px; }
  dl { margin: 0; }
  dd { margin: 0; }

  .stats {
    display: grid;
    grid-template-columns: 1fr 1fr 1.5fr;
    gap: 1px;
    background: #e6dfd1;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e6dfd1;
  }
  .stats > div { background: #fff; padding: 10px 12px; }
  dt {
    font-size: 11px;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ink-soft);
    margin-bottom: 4px;
  }
  .big { font-family: var(--display); font-weight: 700; font-size: 24px; line-height: 1.1; }
  .move dd { font-weight: 650; font-size: 14px; }
  .move .detail { font-weight: 400; font-size: 12px; color: var(--ink-soft); margin-top: 2px; }
  .move.up .sym { color: #2b8a3e; }
  .move.down .sym { color: #c92a2a; }
  .move.new .sym { color: var(--accent); }
  .move.neutral .sym { color: var(--ink-soft); }

  .facts { margin-top: 16px; display: grid; gap: 12px; }
  .facts > div { display: grid; grid-template-columns: 120px 1fr; gap: 10px; align-items: baseline; }
  .facts dt { margin: 0; }
  .facts dd { font-size: 14px; }
  .domains dd { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip {
    font-size: 12px;
    padding: 3px 8px;
    border-radius: 6px;
    background: color-mix(in srgb, var(--set) 10%, #fff);
    border: 1px solid color-mix(in srgb, var(--set) 25%, transparent);
  }

  .note {
    margin-top: 16px;
    padding: 12px 14px;
    border-radius: 12px;
    background: var(--paper-deep);
    border-left: 4px solid var(--set);
    font-size: 13.5px;
    line-height: 1.5;
  }
  .note p { margin: 0; }
  .note-title { font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px !important; color: var(--ink-soft); }

  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 22px 20px;
  }
  .visit {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--ink);
    color: var(--paper);
    text-decoration: none;
    font-weight: 650;
    font-size: 14px;
    padding: 10px 16px;
    border-radius: 999px;
    min-width: 0;
  }
  .visit:hover { background: #24324d; }
  .visit svg { width: 16px; height: 16px; flex: none; fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
  .steps { display: flex; gap: 8px; }
  .steps button {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 1px solid #dcd4c4;
    background: #fff;
    font-size: 22px;
    line-height: 1;
    cursor: pointer;
    color: var(--ink);
  }
  .steps button:hover:not(:disabled) { border-color: var(--set); color: var(--set); }
  .steps button:disabled { opacity: 0.35; cursor: default; }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }

  /* Bottom sheet on phones. */
  @media (max-width: 700px) {
    .card {
      width: 100vw;
      max-width: 100vw;
      margin: auto 0 0;
      max-height: 92vh;
    }
    .sheet { border-radius: 20px 20px 0 0; max-height: 92vh; box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.4); }
    .card[open] { animation: rise 200ms ease-out; }
    h2 { font-size: 34px; }
    .stats { grid-template-columns: 1fr 1fr; }
    .stats .move { grid-column: 1 / -1; }
    .facts > div { grid-template-columns: 1fr; gap: 4px; }
  }
  @keyframes rise { from { transform: translateY(40px); opacity: 0; } }
  @media (prefers-reduced-motion: reduce) {
    .card[open] { animation: none; }
  }
</style>
