"""Write board snapshots and the index the front end reads."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config

log = logging.getLogger(__name__)

BOARD_LABELS = {"world": "World", "uk": "United Kingdom"}


def _previous_ranks(board_name: str, month: str) -> dict[str, int]:
    """Brand -> rank from the most recent earlier snapshot of the same board, if any."""
    earlier = sorted(p for p in config.SNAPSHOT_DIR.glob(f"*/{board_name}.json")
                     if p.parent.name < month)
    if not earlier:
        return {}
    data = json.loads(earlier[-1].read_text())
    return {s["brand"]: s["rank"] for s in data.get("sites", [])}


def board_payload(board: pd.DataFrame, board_name: str, month: str, source: dict,
                  source_key: str, coverage: dict) -> dict:
    prev = _previous_ranks(board_name, month)
    sites = []
    for row in board.itertuples(index=False):
        previous = prev.get(row.brand)
        sites.append({
            "rank": int(row.rank),
            "brand": row.brand,
            "domain": row.domain,
            "category": row.category,
            "group": row.group,
            "source": source_key,
            "source_rank": int(row.source_rank),
            "merged_domains": list(row.merged_domains),
            "previous_rank": previous,
            # Positive = climbed. None when the site is new or there's no earlier month.
            "movement": (previous - int(row.rank)) if previous else None,
        })
    return {
        "board": board_name,
        "label": BOARD_LABELS.get(board_name, board_name),
        "month": month,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metric": "Relative popularity (most visited), not search volume",
        "source": source,
        "coverage": coverage,
        "sites": sites,
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    log.info("Wrote %s", path.relative_to(config.ROOT))


def write_ranked_csv(classified: pd.DataFrame, path: Path, top_n: int = config.RAW_TOP_N) -> None:
    """Publish the raw top-N with how each domain was treated, for transparency."""
    cols = ["rank", "domain", "status", "brand", "category", "reason"]
    path.parent.mkdir(parents=True, exist_ok=True)
    classified.sort_values("rank").head(top_n)[cols].to_csv(path, index=False)
    log.info("Wrote %s", path.relative_to(config.ROOT))


def write_latest_index(categories: pd.DataFrame, board_status: dict[str, dict]) -> dict:
    """Rebuild data/latest.json from every snapshot on disk."""
    months = sorted({p.name for p in config.SNAPSHOT_DIR.iterdir() if p.is_dir()})
    latest = months[-1] if months else None
    boards = {}
    for name in ("world", "uk"):
        available = [m for m in months if (config.SNAPSHOT_DIR / m / f"{name}.json").exists()]
        entry = {
            "label": BOARD_LABELS[name],
            "months": available,
            "latest": f"snapshots/{available[-1]}/{name}.json" if available else None,
            "status": "ok" if available else "pending",
        }
        entry.update(board_status.get(name, {}))
        boards[name] = entry
    groups = (categories.groupby("group", sort=False)["category"].apply(list).to_dict())
    index = {
        "project": "Searchopoly",
        "latest_month": latest,
        "months": months,
        "boards": boards,
        "categories": categories.to_dict("records"),
        "groups": groups,
    }
    write_json(config.LATEST_JSON, index)
    return index
