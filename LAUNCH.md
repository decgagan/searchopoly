# Launch checklist

Everything in the code is ready. These steps need Dec's own accounts, so they are done by hand.
Work through them in order; the whole thing takes about 30 minutes plus DNS waiting time.

## 1. Connect the repo to Cloudflare Pages

Pages can build from a private repo, so this works before the repo is public.

1. Cloudflare dashboard → **Workers & Pages** → **Create application** → **Pages** →
   **Connect to Git**. Sign in with GitHub and give Cloudflare access to `decgagan/searchopoly`
   only (not all repositories).
2. Pick `searchopoly` and **Begin setup**, then use these settings exactly:

   | Setting | Value |
   |---------|-------|
   | Project name | `searchopoly` (gives `searchopoly.pages.dev`) |
   | Production branch | `main` |
   | Framework preset | `None` |
   | Build command | `npm ci --prefix web && npm run build --prefix web` |
   | Build output directory | `web/dist` |
   | Root directory (advanced) | leave blank (the repo root: the build copies `data/` into the site) |

3. **Environment variables (advanced)** → add both, for Production and Preview:

   | Variable | Value | Why |
   |----------|-------|-----|
   | `NODE_VERSION` | `22` | Matches `.node-version` and CI |
   | `SKIP_DEPENDENCY_INSTALL` | `true` | Stops Pages pip-installing the pipeline's `requirements.txt`, which the site doesn't need |

4. **Save and Deploy**. The build takes about a minute. Open `https://searchopoly.pages.dev` and
   check that the board, a site card, `#about`, and `/does-not-exist` (the custom 404 page) all work.

No secrets go into Pages. The site is static, and `web/public/_headers` already sets caching and
security headers.

## 2. Point searchopoly.co.uk at Cloudflare (Namecheap → Cloudflare nameservers)

1. Cloudflare dashboard → **Add a domain** → `searchopoly.co.uk` → **Free** plan. Let it import
   the existing DNS records (if there are any parking records from Namecheap, delete them).
2. Cloudflare shows **two nameservers** (something like `xxx.ns.cloudflare.com` and
   `yyy.ns.cloudflare.com`). Copy them exactly. They are unique to the account.
3. Namecheap → **Domain List** → **Manage** next to `searchopoly.co.uk`:
   - If **DNSSEC** is switched on under **Advanced DNS**, switch it off first.
   - **Nameservers** → choose **Custom DNS** → paste the two Cloudflare nameservers → ✓ save.
4. Back in Cloudflare, click **Check nameservers now**. The domain usually goes **Active**
   within an hour (it can take up to 24 hours). Cloudflare sends an email when it does.

## 3. Add the custom domain to the Pages project

1. **Workers & Pages** → `searchopoly` → **Custom domains** → **Set up a custom domain** →
   `searchopoly.co.uk` → **Activate domain**. Cloudflare creates the DNS record and the
   certificate itself.
2. Repeat for `www.searchopoly.co.uk`. Then send www to the bare domain:
   **searchopoly.co.uk zone → Rules → Redirect Rules → Create rule → template
   "Redirect from WWW to root"** (301, keep the path).
3. Check that `https://searchopoly.co.uk` loads with a padlock. Under **SSL/TLS** → **Edge
   Certificates**, switch on **Always Use HTTPS**.

The canonical URL, `og:url`, `robots.txt` and `sitemap.xml` all already use
`https://searchopoly.co.uk`.

## 4. Add the Radar token so the UK board goes live

1. Cloudflare → **My Profile** → **API Tokens** → **Create Token** → **Create Custom Token** →
   permission **Account → Radar → Read** → create, then copy the token (it is shown once).
2. Add it as a repo secret named `CLOUDFLARE_API_TOKEN`:
   **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**, or
   ```bash
   gh secret set CLOUDFLARE_API_TOKEN --repo decgagan/searchopoly
   ```
3. **Actions → Monthly snapshot → Run workflow** (leave the month blank). It commits the UK data
   and a fresh `og.png`, and that push makes Pages redeploy. The UK toggle loses its "soon" pill.

## 5. Fill in the LinkedIn link

In `web/src/lib/About.svelte`, set `LINKEDIN_URL` (marked `TODO(Dec)`) to the full profile URL,
for example `https://www.linkedin.com/in/your-name/`. The LinkedIn button stays hidden until
this is filled in. Commit and push; Pages redeploys on its own.

## 6. Make the repo public

Do this last, once the site is live and looks right.

- **GitHub repo → Settings → General → Danger Zone → Change visibility → Make public**, or
  `gh repo edit decgagan/searchopoly --visibility public --accept-visibility-change-consequences`.
- This makes the "Source code" links on the site and in the README work for visitors.
- Nothing secret is in the history: the Radar token only ever lives in the Actions secret.
  The repo has been checked for committed tokens.

## 7. Pin it on the GitHub profile

1. Go to `https://github.com/decgagan` → **Customize your pins** → tick `searchopoly` → **Save pins**.
2. On the repo page, click the ⚙ next to **About** and set:
   - Website: `https://searchopoly.co.uk`
   - Description: *The web's most visited sites as a board game, World vs UK, updated monthly.*
   - Topics: `data-visualisation`, `svelte`, `d3`, `python`, `github-actions`, `cloudflare-pages`.
3. Under **Settings → General → Social preview**, upload `web/public/og.png`, so links to the repo
   use the same card.

## After launch: quick checks

- [ ] Paste `https://searchopoly.co.uk` into a LinkedIn post draft (or
      [opengraph.xyz](https://www.opengraph.xyz/)) and check that the share card shows the board image.
- [ ] Open a site card on a phone and press **Share**: the phone's share sheet should open.
- [ ] Submit `https://searchopoly.co.uk/sitemap.xml` in Google Search Console (optional).
- [ ] On the 3rd of next month, check that the **Monthly snapshot** run is green and the site
      updated.
- [ ] If Cloudflare Web Analytics is switched on later, add `https://static.cloudflareinsights.com`
      to `script-src`, and `https://cloudflareinsights.com` to `connect-src`, in
      `web/public/_headers`. The current CSP allows the site's own files only.
