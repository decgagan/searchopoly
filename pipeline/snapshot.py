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


def _previous_file(filename: str, month: str) -> dict | None:
    earlier = sorted(p for p in config.SNAPSHOT_DIR.glob(f"*/{filename}") if p.parent.name < month)
    return json.loads(earlier[-1].read_text()) if earlier else None


def _clean_note(note) -> str | None:
    return note if isinstance(note, str) and note.strip() else None


def category_payload(boards: dict[str, pd.DataFrame], coverage: dict[str, dict], board_name: str,
                     month: str, source: dict, source_key: str,
                     board_size: int = config.BOARD_SIZE,
                     depth: int = config.CATEGORY_DEPTH) -> dict:
    """All category boards for one month in one compact file.

    Brand details (domain, merged domains, note) are stored once in ``brands``; each board
    lists only ids and ranks. Movement compares with the same category board last month.
    """
    filename = f"{board_name}_categories.json"
    prev = _previous_file(filename, month)
    prev_boards = (prev or {}).get("boards", {})
    prev_brands = (prev or {}).get("brands", {})
    brands: dict[str, dict] = {}
    out = {}
    for key, board in boards.items():
        prev_rank = {s["id"]: s["rank"] for s in prev_boards.get(key, {}).get("sites", [])}
        sites = []
        for row in board.itertuples(index=False):
            brands.setdefault(row.id, {
                "brand": row.brand,
                "domain": row.domain,
                "category": row.category,
                "group": row.group,
                "source": source_key,
                "merged_domains": list(row.merged_domains),
                "note": _clean_note(row.note),
            })
            previous = prev_rank.get(row.id)
            sites.append({
                "rank": int(row.rank),
                "id": row.id,
                "source_rank": int(row.source_rank),
                "previous_rank": previous,
                "movement": (previous - int(row.rank)) if previous else None,
            })
        ids = set(board["id"])
        out[key] = {
            "sites": sites,
            "vacant": max(board_size - len(sites), 0),
            "coverage": coverage.get(key, {}),
            "dropped_out": [
                {"id": i, "brand": prev_brands.get(i, {}).get("brand", i), "previous_rank": r}
                for i, r in sorted(prev_rank.items(), key=lambda x: x[1]) if i not in ids
            ],
        }
    return {
        "board": board_name,
        "month": month,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metric": "Relative popularity (most visited) within each colour set, not search volume",
        "source": source,
        "depth": depth,
        "board_size": board_size,
        "has_previous_month": prev is not None,
        "brands": dict(sorted(brands.items())),
        "boards": out,
    }


VOLATILE_KEYS = {"generated_at"}


def _stable(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in VOLATILE_KEYS}


def _is_flat(obj) -> bool:
    values = obj.values() if isinstance(obj, dict) else obj
    return all(not isinstance(v, (dict, list)) or
               (isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v))
               for v in values)


def _dumps(obj, compact: bool, level: int = 0) -> str:
    """Indented JSON. With ``compact``, flat objects (no nested objects) go on one line.

    Category files hold hundreds of small objects; one per line keeps them small but still
    readable in a git diff.
    """
    if not compact:
        return json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)
    if not isinstance(obj, (dict, list)) or not obj or _is_flat(obj):
        return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    pad, inner = "  " * level, "  " * (level + 1)
    if isinstance(obj, dict):
        items = [f"{inner}{json.dumps(k, ensure_ascii=False)}: {_dumps(v, compact, level + 1)}"
                 for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    items = [inner + _dumps(v, compact, level + 1) for v in obj]
    return "[\n" + ",\n".join(items) + "\n" + pad + "]"


def write_json(path: Path, payload: dict, compact: bool = False) -> bool:
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
    path.write_text(_dumps(payload, compact) + "\n")
    log.info("Wrote %s", path.relative_to(config.ROOT))
    return True


def write_ranked_csv(classified: pd.DataFrame, path: Path, top_n: int = config.RAW_TOP_N) -> None:
    """Publish the raw top-N with how each domain was treated, for transparency."""
    cols = ["rank", "domain", "status", "brand", "category", "reason"]
    path.parent.mkdir(parents=True, exist_ok=True)
    classified.sort_values("rank").head(top_n)[cols].to_csv(path, index=False)
    log.info("Wrote %s", path.relative_to(config.ROOT))


def write_latest_index(categories: pd.DataFrame, board_status: dict[str, dict],
                       curation: dict | None = None) -> bool:
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
    category_months = {
        name: [m for m in months if (config.SNAPSHOT_DIR / m / f"{name}_categories.json").exists()]
        for name in ("world", "uk")
    }
    category_boards = {
        "depth": config.CATEGORY_DEPTH,
        "board_size": config.BOARD_SIZE,
        "filters": [{"id": k, "group": g, "label": label}
                    for k, (g, label) in config.CATEGORY_BOARDS.items()],
        "months": {k: v for k, v in category_months.items() if v},
    }
    index = {
        "project": "Searchopoly",
        "latest_month": latest,
        "months": months,
        "boards": boards,
        "categories": categories.to_dict("records"),
        "groups": groups,
        "category_boards": category_boards,
        "curation": curation or {},
    }
    return write_json(config.LATEST_JSON, index)
