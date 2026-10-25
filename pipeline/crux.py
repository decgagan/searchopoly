"""Chrome UX Report (CrUX) country popularity, used to fill the UK board past Radar's top 100.

CrUX publishes, per country and month, the origins Chrome users in that country loaded, in
rank-magnitude buckets (top 1,000, 10,000, ...). Within a bucket there is no order. We read the
GB files mirrored from the public BigQuery tables by github.com/zakird/crux-top-lists
(query: chrome-ux-report.experimental.country). CrUX data is published by Google under
CC BY 4.0: https://developer.chrome.com/docs/crux/about/
"""
from __future__ import annotations

import io
import logging

import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)
URL = "https://raw.githubusercontent.com/zakird/crux-top-lists/main/data/country/{cc}/{yyyymm}.csv.gz"
CACHE = config.ROOT / ".cache" / "crux"


class CruxUnavailable(Exception):
    pass


def top_bucket(month: str, cc: str = "gb", bucket: int = 1000) -> pd.DataFrame:
    """Domains (www. stripped) in CrUX's top ``bucket`` origins for ``cc`` in ``month`` (YYYY-MM)."""
    yyyymm = month.replace("-", "")
    path = CACHE / f"{cc}_{yyyymm}.csv.gz"
    legacy = CACHE / f"{yyyymm}.csv.gz"
    if not path.exists() and cc == "gb" and legacy.exists():
        path = legacy
    if not path.exists():
        resp = requests.get(URL.format(cc=cc, yyyymm=yyyymm), timeout=120)
        if resp.status_code != 200:
            raise CruxUnavailable(f"CrUX {cc.upper()} {month} not published (HTTP {resp.status_code})")
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    df = pd.read_csv(path)
    df = df[df["rank"] <= bucket]
    domains = df["origin"].str.replace(r"^https?://", "", regex=True).str.split(":").str[0]
    log.info("CrUX %s %s: %d origins in the top %d", cc.upper(), month, len(df), bucket)
    return pd.DataFrame({"domain": domains.drop_duplicates().tolist()})


def attribution(month: str) -> dict:
    return {
        "name": "Chrome UX Report (CrUX)",
        "month": month,
        "bucket": 1000,
        "url": "https://developer.chrome.com/docs/crux/",
        "licence_note": "CrUX data by Google, CC BY 4.0. GB country file via github.com/zakird/crux-top-lists.",
    }
