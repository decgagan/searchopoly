"""Fetch Cloudflare Radar domain rankings (https://radar.cloudflare.com/domains).

Endpoint: GET https://api.cloudflare.com/client/v4/radar/ranking/top
Docs: https://developers.cloudflare.com/api/resources/radar/subresources/ranking/methods/top/

The API is free but needs an API token (Cloudflare dashboard > My Profile > API Tokens >
Create Custom Token with the "Account > Radar > Read" permission). Put it in the
CLOUDFLARE_API_TOKEN environment variable. Radar is the only free source we use with a
per-country split, so it powers the UK board.

Radar publishes an ordered ranking for its top 100 domains; deeper ranks are only
available as unordered buckets, which are no use for a board.
"""
from __future__ import annotations

import logging
import os

import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)

API_URL = "https://api.cloudflare.com/client/v4/radar/ranking/top"
TOKEN_ENV = "CLOUDFLARE_API_TOKEN"


class RadarUnavailable(Exception):
    """Raised when Radar can't be used (no token, or the API refused the request)."""


def get_token() -> str | None:
    token = os.environ.get(TOKEN_ENV, "").strip()
    return token or None


def fetch_top(location: str | None = None, limit: int = config.RADAR_LIMIT,
              token: str | None = None, date: str | None = None,
              session: requests.Session | None = None) -> tuple[pd.DataFrame, dict]:
    """Return (DataFrame[rank, domain, radar_categories], meta) for the POPULAR ranking.

    ``location`` is an ISO alpha-2 code such as "GB"; ``None`` means worldwide.
    ``date`` (YYYY-MM-DD) asks for the ranking on that day; ``None`` means the latest.
    """
    token = token or get_token()
    if not token:
        raise RadarUnavailable(
            f"{TOKEN_ENV} is not set, so Cloudflare Radar was skipped. "
            "Create a free token with 'Account > Radar > Read' permission to enable it."
        )

    params = {"limit": limit, "rankingType": "POPULAR", "format": "JSON", "name": "top"}
    if location:
        params["location"] = location
    if date:
        params["date"] = date
    session = session or requests.Session()
    resp = session.get(
        API_URL,
        params=params,
        headers={"Authorization": f"Bearer {token}", "User-Agent": config.USER_AGENT},
        timeout=config.HTTP_TIMEOUT,
    )
    try:
        body = resp.json()
    except ValueError as exc:
        raise RadarUnavailable(f"Radar returned non-JSON (HTTP {resp.status_code})") from exc
    if resp.status_code != 200 or not body.get("success"):
        raise RadarUnavailable(f"Radar request failed (HTTP {resp.status_code}): {body.get('errors')}")

    result = body["result"]
    # The series key matches the "name" param ("top"); fall back to the default "top_0".
    rows = result.get("top") or result.get("top_0") or []
    meta = result.get("meta", {})
    df = pd.DataFrame(
        {
            "rank": [int(r["rank"]) for r in rows],
            "domain": [str(r["domain"]).strip().lower() for r in rows],
            "radar_categories": [
                "; ".join(c.get("name", "") for c in r.get("categories", [])) for r in rows
            ],
        }
    )
    log.info("Radar: %d domains for %s", len(df), location or "worldwide")
    return df, meta


def attribution(meta: dict, location: str | None) -> dict:
    series_meta = meta.get("top") or meta.get("top_0") or {}
    return {
        "name": "Cloudflare Radar",
        "dataset": "Domain Rankings (POPULAR, ordered top 100)",
        "location": location or "worldwide",
        "list_date": series_meta.get("date"),
        "last_updated": meta.get("lastUpdated"),
        "url": "https://radar.cloudflare.com/domains",
        "licence_note": "Cloudflare Radar data, CC BY-NC 4.0 "
                        "(https://creativecommons.org/licenses/by-nc/4.0/). Modified: "
                        "infrastructure domains removed and sibling domains merged.",
    }
