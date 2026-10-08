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


def _previous_sites(board_name: str, month: str) -> list[dict]:
    """Sites from the most recent earlier snapshot of the same board, if any."""
    earlier = sorted(p for p in config.SNAPSHOT_DIR.glob(f"*/{board_name}.json")
                     if p.parent.name < month)
    if not earlier:
        return []
    return json.loads(earlier[-1].read_text()).get("sites", [])


def has_earlier_snapshot(board_name: str, month: str) -> bool:
    return any(p.parent.name < month for p in config.SNAPSHOT_DIR.glob(f"*/{board_name}.json"))


def board_payload(board: pd.DataFrame, board_name: str, month: str, source: dict,
                  source_key: str, coverage: dict) -> dict:
    prev_sites = _previous_sites(board_name, month)
    prev = {s["brand"]: s["rank"] for s in prev_sites}
    sites = []
    for row in board.itertuples(index=False):
        previous = prev.get(row.brand)
        sites.append({
            "rank": int(row.rank),
            "id": row.id,
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
            "note": row.note if isinstance(row.note, str) and row.note.strip() else None,
        })
    return {
        "board": board_name,
        "label": BOARD_LABELS.get(board_name, board_name),
        "month": month,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metric": "Relative popularity (most visited), not search volume",
        "source": source,
        "coverage": coverage,
        "has_previous_month": has_earlier_snapshot(board_name, month),
        "sites": sites,
        # On last month's board but not this one.
        "dropped_out": [
            {"id": s.get("id"), "brand": s["brand"], "previous_rank": s["rank"]}
            for s in prev_sites if s["brand"] not in set(board["brand"])
        ],
    }


VOLATILE_KEYS = {"generated_at"}


def _stable(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in VOLATILE_KEYS}


def write_json(path: Path, payload: dict) -> bool:
    """Write ``payload`` unless only volatile fields (timestamps) would change.

    Keeps re-runs idempotent, so the monthly job only commits when the data really changed.
    Returns True if the file was written.
    """
    if path.exists():
        try:
            if _stable(json.loads(path.read_text())) == _stable(payload):
                log.info("Unchanged %s", path.relative_to(config.ROOT))
                return False
        except ValueError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    log.info("Wrote %s", path.relative_to(config.ROOT))
    return True


def write_ranked_csv(classified: pd.DataFrame, path: Path, top_n: int = config.RAW_TOP_N) -> None:
    """Publish the raw top-N with how each domain was treated, for transparency."""
    cols = ["rank", "domain", "status", "brand", "category", "reason"]
    path.parent.mkdir(parents=True, exist_ok=True)
    classified.sort_values("rank").head(top_n)[cols].to_csv(path, index=False)
    log.info("Wrote %s", path.relative_to(config.ROOT))


def write_latest_index(categories: pd.DataFrame, board_status: dict[str, dict]) -> bool:
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
        status = board_status.get(name, {})
        if available and status.get("status") == "pending":
            # Older snapshots exist, so keep the board live and just note why this run skipped it.
            entry["note"] = status.get("reason")
        else:
            entry.update(status)
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
    return write_json(config.LATEST_JSON, index)
