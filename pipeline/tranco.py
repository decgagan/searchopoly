"""Fetch the Tranco research ranking (https://tranco-list.eu).

Tranco gives every daily list a permanent ID, which we record so each snapshot can be
cited and reproduced exactly.
"""
from __future__ import annotations

import io
import json
import logging
import time

import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)

API_BY_DATE = "https://tranco-list.eu/api/lists/date/{date}"
LIST_PAGE = "https://tranco-list.eu/list/{list_id}"


_last_call = 0.0


def _get(session: requests.Session, url: str, retries: int = 4) -> requests.Response:
    """GET with Tranco's 1 request/second API limit respected, retrying on HTTP 429."""
    global _last_call
    for attempt in range(retries + 1):
        wait = 1.1 - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        resp = session.get(url, timeout=config.HTTP_TIMEOUT)
        if resp.status_code != 429 or attempt == retries:
            return resp
        time.sleep(2 ** attempt)
    return resp


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = config.USER_AGENT
    return s


class TrancoUnavailable(Exception):
    """Raised when the requested daily list doesn't exist (yet)."""


def list_meta(date: str = "latest", session: requests.Session | None = None) -> dict:
    """Metadata for the daily Tranco list of ``date`` (YYYY-MM-DD) or "latest".

    The list for day D is published around 22:00 UTC on D and averages the 30 days up to D.
    """
    key = date.replace("-", "")
    # Past lists never change, so their metadata is cached; "latest" always hits the API.
    cache_file = config.CACHE_DIR / f"tranco_meta_{key}.json"
    if key != "latest" and cache_file.exists():
        return json.loads(cache_file.read_text())
    session = session or _session()
    resp = _get(session, API_BY_DATE.format(date=key))
    if resp.status_code == 404:
        raise TrancoUnavailable(f"No Tranco list for {date} (it appears around 22:00 UTC that day).")
    resp.raise_for_status()
    meta = resp.json()
    if not meta.get("available") or meta.get("failed"):
        raise TrancoUnavailable(f"Tranco list for {date} is not available: {meta}")
    if key != "latest":
        config.CACHE_DIR.mkdir(exist_ok=True)
        cache_file.write_text(json.dumps(meta))
    return meta


def latest_list_meta(session: requests.Session | None = None) -> dict:
    return list_meta("latest", session)


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
        resp = _get(session, url)
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
