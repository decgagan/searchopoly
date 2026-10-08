<script>
  import { monthLabel } from "./format.js";

  // TODO(Dec): paste your LinkedIn profile URL here, e.g. "https://www.linkedin.com/in/your-name/".
  // The LinkedIn link stays hidden until this is filled in.
  const LINKEDIN_URL = "";
  const GITHUB_PROFILE = "https://github.com/decgagan";
  const REPO = "https://github.com/decgagan/searchopoly";

  let { index, world = null } = $props();

  const months = $derived(index?.boards?.world?.months ?? []);
  const curation = $derived(index?.curation ?? {});
  const source = $derived(world?.source);
  const ukLive = $derived(index?.boards?.uk?.status === "ok");
</script>

<article class="about" aria-labelledby="about-title">
  <a class="back" href="#world">← Back to the board</a>

  <header>
    <p class="kicker">How it's made</p>
    <h1 id="about-title">The web's most visited sites, measured honestly</h1>
    <p class="lede">
      Searchopoly turns open website-popularity rankings into a game board. The interesting part
      isn't the board, though. It's the pipeline that turns noisy, infrastructure-heavy domain lists
      into a clean, explainable ranking of the sites people actually visit.
    </p>
  </header>

  <ul class="stats" aria-label="Project in numbers">
    <li><strong>{months.length}</strong><span>months tracked</span></li>
    <li><strong>28</strong><span>sites per board</span></li>
    <li><strong>500</strong><span>raw domains reviewed per month</span></li>
    <li><strong>{curation.excluded_domains ?? "350+"}</strong><span>background domains filtered out</span></li>
  </ul>

  <section>
    <h2>Most visited, not most searched</h2>
    <p>
      The board ranks sites by <strong>relative popularity of visits</strong>. "Most searched" would
      need paid keyword tools and measures something different: what people type into Google, not
      where they end up. The rankings used here don't publish visitor numbers, so Searchopoly shows
      positions only and never invents traffic figures.
    </p>
  </section>

  <section>
    <h2>Where the data comes from</h2>
    <dl class="sources">
      <div>
        <dt>World board: <a href="https://tranco-list.eu" target="_blank" rel="noopener">Tranco</a></dt>
        <dd>
          A research ranking from KU Leuven and partners that averages five popularity lists (Chrome
          UX Report, Cloudflare Radar, Cisco Umbrella, Majestic and Farsight) over 30 days, which
          makes it much harder to game than any single list. Each month uses the list dated the 1st,
          and every snapshot records its permanent list ID{#if source}, e.g.
          <a href={source.url} target="_blank" rel="noopener">{source.list_id}</a> for {monthLabel(world.month)}{/if}.
        </dd>
      </div>
      <div>
        <dt>UK board: <a href="https://radar.cloudflare.com/domains" target="_blank" rel="noopener">Cloudflare Radar</a></dt>
        <dd>
          Cloudflare's ranking of the top 100 domains by country, based on its 1.1.1.1 DNS resolver.
          {#if ukLive}It powers the UK board.{:else}The UK board switches on as soon as the Radar
          connection is added; until then it shows "coming soon" rather than a guess.{/if}
          Tranco has no country split, and estimating the UK from <code>.uk</code> domains would be
          wrong, as most UK traffic goes to <code>.com</code> sites.
        </dd>
      </div>
    </dl>
  </section>

  <section>
    <h2>How the list is cleaned</h2>
    <ol class="steps">
      <li>
        <strong>Classify every domain.</strong> Raw lists are dominated by domains nobody visits on
        purpose: CDNs, DNS, ad servers, telemetry and update hosts. Each of the top 500 domains is
        matched against a hand-curated list of {curation.mapped_domains ?? "about 280"} real sites,
        an exclude list of {curation.excluded_domains ?? "about 350"} background domains (each with a
        reason), and {curation.infra_patterns ?? "about 40"} infrastructure name patterns.
      </li>
      <li>
        <strong>Merge sibling domains into brands.</strong> <code>google.com</code>,
        <code>google.co.uk</code> and <code>gmail.com</code> become Google;
        <code>twitter.com</code> and <code>x.com</code> become X. A brand takes its best rank.
      </li>
      <li>
        <strong>Check coverage.</strong> Any domain that hasn't been reviewed is kept off the board.
        If one ranks above the 28th site, the monthly run flags it for review, because a real site
        might be missing.
      </li>
      <li>
        <strong>Leave out adult sites</strong> entirely.
      </li>
    </ol>
  </section>

  <section>
    <h2>Known biases</h2>
    <ul class="biases">
      <li>
        <strong>Background traffic.</strong> Several of Tranco's sources count DNS lookups, which
        can't tell a person visiting a site from a device checking in. Microsoft, Apple, Bing and
        Adobe are probably ranked higher than real visits alone would justify. They stay in, with a
        note on their site cards, rather than being quietly adjusted.
      </li>
      <li>
        <strong>Regional giants.</strong> Mail.ru and Dzen rank surprisingly high for a world board,
        partly because DNS-based sources reward services with large regional user bases.
      </li>
      <li>
        <strong>Ranks, not traffic.</strong> A gap of one place can hide a huge or tiny difference in
        visits. Movement between months is real but small changes shouldn't be over-read.
      </li>
      <li>
        <strong>Human judgement.</strong> Deciding what counts as a "real" site is a curation call.
        Every decision is in the open: the raw top 500 for each month, with how each domain was
        treated, is published as a CSV in the repository.
      </li>
    </ul>
  </section>

  <section>
    <h2>Monthly updates</h2>
    <p>
      On the 3rd of each month a GitHub Actions job runs the tests, builds the new month's boards,
      writes a report of movers and any domains that need reviewing, and commits the data. The site
      then rebuilds automatically. Re-runs are idempotent: nothing is committed unless the data has
      actually changed.
    </p>
  </section>

  <section>
    <h2>Tech stack</h2>
    <ul class="stack">
      <li><span>Data pipeline</span> Python, pandas, requests, pytest</li>
      <li><span>Front end</span> Svelte 5, Vite, D3 (rank charts), CSS grid board</li>
      <li><span>Automation</span> GitHub Actions (monthly snapshot and CI)</li>
      <li><span>Hosting</span> Cloudflare Pages, static, no server</li>
      <li><span>Privacy</span> no cookies, no tracking, no third-party requests</li>
    </ul>
  </section>

  <section>
    <h2>Licences and credits</h2>
    <ul class="credits">
      <li>
        World data: Tranco, from Le Pochat et al., "Tranco: A Research-Oriented Top Sites Ranking
        Hardened Against Manipulation", NDSS 2019,
        <a href="https://doi.org/10.14722/ndss.2019.23386" target="_blank" rel="noopener">doi:10.14722/ndss.2019.23386</a>.
      </li>
      <li>
        Cloudflare Radar data is licensed
        <a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank" rel="noopener">CC BY-NC 4.0</a>
        and also feeds into Tranco, so Searchopoly is strictly non-commercial. The data has been
        modified: background domains removed, sibling domains merged and categories added.
      </li>
      <li>Code: MIT licence. Fonts: Space Grotesk and Inter (SIL Open Font Licence), self-hosted.</li>
      <li>
        Not affiliated with any board game publisher, or with Tranco, Cloudflare or any site shown.
        Brand names belong to their owners and are used only to identify the sites.
      </li>
    </ul>
  </section>

  <section class="author">
    <h2>Built by Dec</h2>
    <p>
      Searchopoly is a portfolio project by Dec, a Data Science student in the UK. It covers the
      full journey: sourcing and citing open data, cleaning it with documented rules, testing the
      pipeline, automating monthly updates and presenting the result as something people want to
      explore.
    </p>
    <p class="links">
      <a href={GITHUB_PROFILE} target="_blank" rel="noopener">GitHub: decgagan</a>
      <a href={REPO} target="_blank" rel="noopener">Source code</a>
      {#if LINKEDIN_URL}<a href={LINKEDIN_URL} target="_blank" rel="noopener">LinkedIn</a>{/if}
    </p>
  </section>

  <a class="back bottom" href="#world">← Back to the board</a>
</article>

<style>
  .about {
    width: min(760px, calc(100vw - 24px));
    background: var(--paper);
    border-radius: 20px;
    padding: clamp(24px, 5vw, 56px);
    box-shadow: 0 0 0 8px var(--frame), 0 30px 80px -20px rgba(0, 0, 0, 0.6);
    color: var(--ink);
    line-height: 1.6;
    font-size: 16px;
  }
  .back {
    display: inline-block;
    color: var(--accent);
    font-weight: 650;
    text-decoration: none;
    font-size: 14px;
  }
  .back:hover { text-decoration: underline; }
  .back.bottom { margin-top: 28px; }
  .kicker {
    margin: 24px 0 6px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent);
  }
  h1 {
    margin: 0;
    font-family: var(--display);
    font-size: clamp(30px, 5vw, 44px);
    line-height: 1.05;
    letter-spacing: -0.03em;
  }
  .lede { font-size: 18px; color: #344054; margin: 16px 0 0; }

  .stats {
    list-style: none;
    padding: 0;
    margin: 28px 0 8px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
  }
  .stats li {
    background: var(--paper-deep);
    border-radius: 12px;
    padding: 14px;
    display: flex;
    flex-direction: column;
  }
  .stats strong { font-family: var(--display); font-size: 28px; line-height: 1; }
  .stats span { font-size: 13px; color: var(--ink-soft); margin-top: 6px; line-height: 1.3; }

  section { margin-top: 32px; }
  h2 {
    font-family: var(--display);
    font-size: 22px;
    letter-spacing: -0.01em;
    margin: 0 0 10px;
    padding-top: 22px;
    border-top: 1px solid #e6dfd1;
  }
  p { margin: 0 0 12px; }
  a { color: inherit; text-decoration-color: color-mix(in srgb, var(--accent) 60%, transparent); text-underline-offset: 2px; }
  code { font-size: 0.9em; background: var(--paper-deep); padding: 0.1em 0.35em; border-radius: 4px; }

  .sources { margin: 0; display: grid; gap: 14px; }
  .sources dt { font-weight: 700; }
  .sources dd { margin: 2px 0 0; color: #344054; }

  .steps, .biases, .credits { padding-left: 1.2em; margin: 0; display: grid; gap: 10px; color: #344054; }
  .steps strong, .biases strong { color: var(--ink); }

  .stack { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
  .stack li { display: grid; grid-template-columns: 140px 1fr; gap: 12px; color: #344054; }
  .stack span { font-weight: 700; color: var(--ink); }

  .author { background: var(--paper-deep); border-radius: 14px; padding: 4px 22px 18px; }
  .author h2 { border-top: 0; }
  .links { display: flex; flex-wrap: wrap; gap: 10px; margin: 0; }
  .links a {
    text-decoration: none;
    font-weight: 650;
    font-size: 14px;
    padding: 8px 14px;
    border-radius: 999px;
    background: var(--ink);
    color: var(--paper);
  }
  .links a:hover { background: #24324d; }

  @media (max-width: 700px) {
    .stats { grid-template-columns: repeat(2, 1fr); }
    .stack li { grid-template-columns: 1fr; gap: 0; }
  }
</style>
