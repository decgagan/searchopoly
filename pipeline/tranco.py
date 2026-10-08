"""Fetch the Tranco research ranking (https://tranco-list.eu).

Tranco gives every daily list a permanent ID, which we record so each snapshot can be
cited and reproduced exactly.
"""
from __future__ import annotations

import io
import logging

import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)

API_LATEST = "https://tranco-list.eu/api/lists/date/latest"
LIST_PAGE = "https://tranco-list.eu/list/{list_id}"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = config.USER_AGENT
    return s


def latest_list_meta(session: requests.Session | None = None) -> dict:
    """Return metadata for the latest daily Tranco list (ID, creation date, providers)."""
    session = session or _session()
    resp = session.get(API_LATEST, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    meta = resp.json()
    if not meta.get("available") or meta.get("failed"):
        raise RuntimeError(f"Latest Tranco list is not available: {meta}")
    return meta


def download_list(meta: dict, top_n: int = config.TRANCO_FETCH_N,
                  session: requests.Session | None = None) -> pd.DataFrame:
    """Download the first ``top_n`` rows of a Tranco list as a DataFrame (rank, domain).

    Results are cached in ``.cache/`` keyed by list ID, so re-runs are offline-friendly.
    """
    list_id = meta["list_id"]
    config.CACHE_DIR.mkdir(exist_ok=True)
    cache_file = config.CACHE_DIR / f"tranco_{list_id}_top{top_n}.csv"

    if cache_file.exists():
        log.info("Tranco: using cached list %s (%s)", list_id, cache_file.name)
        text = cache_file.read_text()
    else:
        session = session or _session()
        url = f"https://tranco-list.eu/download/{list_id}/{top_n}"
        log.info("Tranco: downloading top %d of list %s", top_n, list_id)
        resp = session.get(url, timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        text = resp.text
        cache_file.write_text(text)

    df = pd.read_csv(io.StringIO(text), header=None, names=["rank", "domain"])
    df["rank"] = df["rank"].astype(int)
    df["domain"] = df["domain"].astype(str).str.strip().str.lower()
    log.info("Tranco: %d rows loaded", len(df))
    return df


def attribution(meta: dict) -> dict:
    """Source block written into every snapshot built from Tranco."""
    cfg = meta.get("configuration", {})
    return {
        "name": "Tranco",
        "list_id": meta["list_id"],
        "list_date": meta["created_on"][:10],
        "window": f"{cfg.get('startDate')} to {cfg.get('endDate')}",
        "providers": cfg.get("providers", []),
        "url": LIST_PAGE.format(list_id=meta["list_id"]),
        "citation": (
            "Le Pochat et al. (2019), 'Tranco: A Research-Oriented Top Sites Ranking "
            "Hardened Against Manipulation', NDSS 2019. https://doi.org/10.14722/ndss.2019.23386"
        ),
        "licence_note": (
            "Tranco aggregates Cisco Umbrella, Majestic (CC BY 3.0), Farsight, Chrome UX "
            "Report and Cloudflare Radar (CC BY-NC 4.0) rankings. Non-commercial use."
        ),
    }
