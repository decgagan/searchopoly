"""Turn a raw domain ranking into a clean list of user-facing websites.

Raw popularity lists are dominated by domains nobody visits on purpose: CDNs, DNS,
ad servers, telemetry and API hosts that your devices contact in the background.
We classify every domain into one of three buckets:

* ``mapped``     - listed in ``site_map.csv``: a real destination, tagged with a brand
                   and category. Sibling domains (google.com, google.co.uk) share a brand.
* ``excluded``   - listed in ``exclude.csv`` or matching an infrastructure pattern.
* ``unreviewed`` - neither. Never shown on a board, but reported so the map can be extended.

The site map always wins over the patterns, and the explicit exclude list wins over the
site map (so a domain can't be both).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import pandas as pd

from . import config

log = logging.getLogger(__name__)

# Background/infrastructure naming patterns. Only applied to domains that are not in the
# site map, so a real site that happens to match is safe once it's mapped.
INFRA_PATTERNS = [
    r"cdn", r"dns", r"akamai", r"akam\.net$", r"edgekey", r"edgesuite", r"msedge",
    r"amazonaws", r"awsglobal", r"azure", r"cloudfront", r"fastly", r"doubleclick",
    r"googleapis", r"gstatic", r"googlesyndication", r"googletag", r"googleadservices",
    r"google-analytics", r"googleusercontent", r"googlevideo", r"^gvt\d", r"analytics",
    r"adsystem", r"adserv", r"adsrvr", r"telemetry", r"metrics", r"tracking",
    r"trafficmanager", r"windowsupdate", r"connecttest", r"msftncsi", r"captiveportal",
    r"portal-detection", r"root-servers", r"gtld-servers", r"\.arpa$", r"edgecast",
    r"workers\.dev$", r"pages\.dev$", r"crashlytics", r"app-measurement",
]
_INFRA_RE = re.compile("|".join(INFRA_PATTERNS))


def slugify(brand: str) -> str:
    """URL-safe, stable ID for a brand, e.g. 'X (Twitter)' -> 'x-twitter'."""
    return re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")


def normalise_domain(domain: str) -> str:
    d = str(domain).strip().lower().rstrip(".")
    if d.startswith("www."):
        d = d[4:]
    return d


@dataclass
class Rules:
    site_map: pd.DataFrame       # domain, brand, canonical_domain, category, note (optional)
    excludes: pd.DataFrame       # domain, reason
    categories: pd.DataFrame     # category, group, label

    @property
    def map_lookup(self) -> dict[str, dict]:
        return self.site_map.set_index("domain").to_dict("index")

    @property
    def exclude_lookup(self) -> dict[str, str]:
        return dict(zip(self.excludes["domain"], self.excludes["reason"]))

    @property
    def group_lookup(self) -> dict[str, str]:
        return dict(zip(self.categories["category"], self.categories["group"]))


def load_rules(site_map_path=config.SITE_MAP_CSV, exclude_path=config.EXCLUDE_CSV,
               categories_path=config.CATEGORIES_CSV) -> Rules:
    site_map = pd.read_csv(site_map_path, comment="#", skipinitialspace=True, dtype=str)
    excludes = pd.read_csv(exclude_path, comment="#", skipinitialspace=True, dtype=str)
    categories = pd.read_csv(categories_path, comment="#", skipinitialspace=True, dtype=str)
    if "note" not in site_map.columns:
        site_map["note"] = None
    for frame in (site_map, excludes):
        frame["domain"] = frame["domain"].map(normalise_domain)
    validate_rules(site_map, excludes, categories)
    return Rules(site_map=site_map, excludes=excludes, categories=categories)


def validate_rules(site_map: pd.DataFrame, excludes: pd.DataFrame,
                   categories: pd.DataFrame) -> None:
    """Fail loudly on mistakes in the hand-curated files."""
    problems = []
    dupes = site_map["domain"][site_map["domain"].duplicated()].tolist()
    if dupes:
        problems.append(f"duplicate domains in site_map: {dupes}")
    dupes = excludes["domain"][excludes["domain"].duplicated()].tolist()
    if dupes:
        problems.append(f"duplicate domains in exclude list: {dupes}")
    both = sorted(set(site_map["domain"]) & set(excludes["domain"]))
    if both:
        problems.append(f"domains in both site_map and exclude list: {both}")
    bad_cats = sorted(set(site_map["category"]) - set(categories["category"]))
    if bad_cats:
        problems.append(f"unknown categories in site_map: {bad_cats}")
    slugs = site_map.drop_duplicates("brand")["brand"].map(slugify)
    if slugs.duplicated().any():
        problems.append(f"brands with clashing URL ids: {slugs[slugs.duplicated()].tolist()}")
    if site_map[["brand", "canonical_domain", "category"]].isna().any().any():
        problems.append("site_map has blank brand/canonical_domain/category cells")
    # Every row of one brand must agree on canonical domain and category.
    per_brand = site_map.groupby("brand")[["canonical_domain", "category"]].nunique()
    inconsistent = per_brand[(per_brand > 1).any(axis=1)].index.tolist()
    if inconsistent:
        problems.append(f"brands with conflicting canonical_domain/category: {inconsistent}")
    if problems:
        raise ValueError("Invalid curation files:\n  - " + "\n  - ".join(problems))


def classify(ranked: pd.DataFrame, rules: Rules) -> pd.DataFrame:
    """Add status/brand/category/reason columns to a (rank, domain) ranking."""
    mapped = rules.map_lookup
    excluded = rules.exclude_lookup
    groups = rules.group_lookup

    out = ranked.copy()
    out["domain"] = out["domain"].map(normalise_domain)
    status, brand, canonical, category, group, reason, note = [], [], [], [], [], [], []
    for d in out["domain"]:
        if d in excluded:
            status.append("excluded"); reason.append(excluded[d]); note.append(None)
            brand.append(None); canonical.append(None); category.append(None); group.append(None)
        elif d in mapped:
            m = mapped[d]
            status.append("mapped"); reason.append(None)
            brand.append(m["brand"]); canonical.append(m["canonical_domain"])
            category.append(m["category"]); group.append(groups.get(m["category"]))
            n = m.get("note")
            note.append(n if isinstance(n, str) and n.strip() else None)
        elif _INFRA_RE.search(d):
            status.append("excluded"); reason.append("infrastructure (name pattern)"); note.append(None)
            brand.append(None); canonical.append(None); category.append(None); group.append(None)
        else:
            status.append("unreviewed"); reason.append(None); note.append(None)
            brand.append(None); canonical.append(None); category.append(None); group.append(None)
    out["status"] = status
    out["brand"] = brand
    out["canonical_domain"] = canonical
    out["category"] = category
    out["group"] = group
    out["reason"] = reason
    out["note"] = note
    return out


def build_board(classified: pd.DataFrame, board_size: int = config.BOARD_SIZE) -> pd.DataFrame:
    """Merge mapped domains into brands and keep the top ``board_size``.

    A brand takes the best (lowest) rank of any of its domains.
    """
    columns = ["rank", "id", "brand", "domain", "category", "group", "source_rank",
               "merged_domains", "note"]
    mapped = classified[classified["status"] == "mapped"].sort_values("rank")
    if mapped.empty:
        return pd.DataFrame(columns=columns)
    agg = (
        mapped.groupby("brand", sort=False)
        .agg(
            source_rank=("rank", "min"),
            domain=("canonical_domain", "first"),
            category=("category", "first"),
            group=("group", "first"),
            merged_domains=("domain", list),
            note=("note", lambda s: next((n for n in s if isinstance(n, str)), None)),
        )
        .reset_index()
        .sort_values("source_rank", kind="stable")
        .head(board_size)
        .reset_index(drop=True)
    )
    agg.insert(0, "rank", range(1, len(agg) + 1))
    agg["id"] = agg["brand"].map(slugify)
    return agg[columns]


def coverage_check(classified: pd.DataFrame, board: pd.DataFrame) -> dict:
    """Report whether any unreviewed domain outranks the last site on the board.

    If one does, it might belong on the board, so the site map needs extending.
    """
    last_rank = int(board["source_rank"].max()) if not board.empty else int(classified["rank"].max())
    unreviewed = classified[(classified["status"] == "unreviewed")]
    first_unreviewed = int(unreviewed["rank"].min()) if not unreviewed.empty else None
    blocking = unreviewed[unreviewed["rank"] <= last_rank]["domain"].tolist()
    return {
        "last_board_source_rank": last_rank,
        "reviewed_through_rank": (first_unreviewed - 1) if first_unreviewed else int(classified["rank"].max()),
        "unreviewed_above_cutoff": blocking,
        "ok": not blocking,
    }
