"""Run the whole pipeline.

    python -m pipeline.run                       # this month's snapshot
    python -m pipeline.run --month 2026-09       # a specific month
    python -m pipeline.run --backfill 2026-01:2026-10

Each month's World board uses the Tranco list dated the 1st of that month (covering the
previous 30 days), so months are comparable and every snapshot is reproducible from its list
ID. The UK board uses Cloudflare Radar (location=GB) for the same date; it needs
CLOUDFLARE_API_TOKEN and is skipped (marked pending) without it.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime, timezone

from . import clean, config, radar, report, snapshot, tranco

log = logging.getLogger("pipeline")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def month_range(start: str, end: str) -> list[str]:
    y, m = map(int, start.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= end:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def build_world(rules: clean.Rules, month: str, board_size: int) -> report.BoardResult:
    date = f"{month}-01"
    try:
        meta = tranco.list_meta(date)
    except tranco.TrancoUnavailable as exc:
        return report.BoardResult("world", month, "failed", message=str(exc))
    ranked = tranco.download_list(meta)
    classified = clean.classify(ranked, rules)
    board = clean.build_board(classified, board_size)
    coverage = clean.coverage_check(classified, board)
    source = tranco.attribution(meta)
    payload = snapshot.board_payload(board, "world", month, source, "tranco", coverage)
    out_dir = config.SNAPSHOT_DIR / month
    changed = snapshot.write_json(out_dir / "world.json", payload)
    snapshot.write_ranked_csv(classified, out_dir / "world_ranked_top500.csv")
    return report.BoardResult(
        "world", month, "ok", source=f"Tranco list {meta['list_id']} ({source['window']})",
        payload=payload, coverage=coverage, changed=changed,
        unreviewed=report.unreviewed_domains(classified),
    )


def build_uk(rules: clean.Rules, month: str, board_size: int) -> report.BoardResult:
    date = f"{month}-01"
    try:
        ranked, meta = radar.fetch_top(location="GB", date=date)
    except radar.RadarUnavailable as exc:
        log.warning("UK board pending: %s", exc)
        return report.BoardResult("uk", month, "pending", message=str(exc))
    classified = clean.classify(ranked, rules)
    board = clean.build_board(classified, board_size)
    coverage = clean.coverage_check(classified, board)
    if len(board) < board_size:
        log.warning("UK: only %d user-facing sites in Radar's top %d", len(board), len(ranked))
    source = radar.attribution(meta, "GB")
    payload = snapshot.board_payload(board, "uk", month, source, "cloudflare_radar", coverage)
    out_dir = config.SNAPSHOT_DIR / month
    changed = snapshot.write_json(out_dir / "uk.json", payload)
    snapshot.write_ranked_csv(classified, out_dir / "uk_ranked_top100.csv", top_n=config.RADAR_LIMIT)
    return report.BoardResult(
        "uk", month, "ok", source=f"Cloudflare Radar GB top {len(ranked)} ({source['list_date']})",
        payload=payload, coverage=coverage, changed=changed,
        unreviewed=report.unreviewed_domains(classified, config.RADAR_LIMIT),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Searchopoly board snapshots.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--month", help="Snapshot month as YYYY-MM (default: current month, UTC)")
    group.add_argument("--backfill", metavar="FROM:TO", help="Build every month in a range, oldest first")
    parser.add_argument("--board-size", type=int, default=config.BOARD_SIZE)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.backfill:
        start, _, end = args.backfill.partition(":")
        if not (MONTH_RE.match(start) and MONTH_RE.match(end)) or start > end:
            parser.error("--backfill needs FROM:TO as YYYY-MM:YYYY-MM")
        months = month_range(start, end)
    else:
        month = args.month or datetime.now(timezone.utc).strftime("%Y-%m")
        if not MONTH_RE.match(month):
            parser.error("--month needs YYYY-MM")
        months = [month]

    rules = clean.load_rules()
    results = []
    for month in months:  # oldest first, so movement is computed against the month before
        results.append(build_world(rules, month, args.board_size))
        results.append(build_uk(rules, month, args.board_size))

    last = {r.board: r for r in results}
    status = {
        b: ({"status": "pending", "reason": r.message.split(".")[0] + "."} if r.status == "pending" else {})
        for b, r in last.items()
    }
    snapshot.write_latest_index(rules.categories, status)
    report.publish(results)

    failed = [r for r in results if r.board == "world" and r.status == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
