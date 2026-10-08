<script>
  let { corner } = $props();
</script>

<div class="corner {corner.id}" style:grid-row={corner.row} style:grid-column={corner.col}>
  <svg class="icon" viewBox="0 0 48 48" aria-hidden="true">
    {#if corner.icon === "arrow"}
      <path d="M40 24H10m0 0 11-11M10 24l11 11" />
    {:else if corner.icon === "spinner"}
      <circle cx="24" cy="24" r="15" opacity="0.25" />
      <path d="M24 9a15 15 0 0 1 15 15" />
    {:else if corner.icon === "mask"}
      <path d="M6 22c4-2 9-3 18-3s14 1 18 3" />
      <circle cx="15" cy="30" r="6" /><circle cx="33" cy="30" r="6" />
      <path d="M21 30h6" />
    {:else}
      <path d="M8 12h32v24H8z" /><path d="M8 19h32" /><path d="m19 25 10 7m0-7-10 7" />
    {/if}
  </svg>
  <span class="title">{corner.title}</span>
  <span class="text">{corner.text}</span>
</div>

<style>
  .corner {
    background: var(--paper);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: calc(var(--u) * 0.12);
    gap: calc(var(--u) * 0.04);
  }
  .icon {
    width: calc(var(--u) * 0.48);
    height: calc(var(--u) * 0.48);
    fill: none;
    stroke: var(--accent);
    stroke-width: 3.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .title {
    font-family: var(--display);
    font-weight: 700;
    font-size: calc(var(--u) * 0.2);
    line-height: 1;
    color: var(--ink);
    letter-spacing: -0.01em;
  }
  .text {
    font-size: calc(var(--u) * 0.09);
    color: var(--ink-soft);
    line-height: 1.25;
    max-width: 12ch;
  }
  .logon { background: color-mix(in srgb, var(--accent) 12%, var(--paper)); }
</style>
