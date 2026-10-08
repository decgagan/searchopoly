"""Run the whole pipeline: `python -m pipeline.run`.

1. World board  <- latest Tranco list (no token needed).
2. UK board     <- Cloudflare Radar, location=GB (needs CLOUDFLARE_API_TOKEN; skipped if absent).
3. Clean, merge brands, write data/snapshots/YYYY-MM/*.json and data/latest.json.
"""
from __future__ import annotations

import argparse
import logging
import sys

from . import clean, config, radar, snapshot, tranco

log = logging.getLogger("pipeline")


def build_world(rules: clean.Rules, month: str | None, board_size: int) -> tuple[str, dict]:
    meta = tranco.latest_list_meta()
    ranked = tranco.download_list(meta)
    month = month or meta["created_on"][:7]
    classified = clean.classify(ranked, rules)
    board = clean.build_board(classified, board_size)
    coverage = clean.coverage_check(classified, board)
    if not coverage["ok"]:
        log.warning("World: unreviewed domains outrank the last board site, extend "
                    "pipeline/data/site_map.csv or exclude.csv: %s",
                    coverage["unreviewed_above_cutoff"])
    out_dir = config.SNAPSHOT_DIR / month
    snapshot.write_json(out_dir / "world.json", snapshot.board_payload(
        board, "world", month, tranco.attribution(meta), "tranco", coverage))
    snapshot.write_ranked_csv(classified, out_dir / "world_ranked_top500.csv")
    log.info("World top 5: %s", ", ".join(board["brand"].head(5)))
    return month, {"source": "tranco", "list_id": meta["list_id"]}


def build_uk(rules: clean.Rules, month: str, board_size: int) -> dict:
    try:
        ranked, meta = radar.fetch_top(location="GB")
    except radar.RadarUnavailable as exc:
        log.warning("UK board pending: %s", exc)
        return {"status": "pending", "reason": str(exc).split(".")[0] + "."}
    classified = clean.classify(ranked, rules)
    board = clean.build_board(classified, board_size)
    coverage = clean.coverage_check(classified, board)
    if len(board) < board_size:
        log.warning("UK: only %d user-facing sites in Radar's top %d", len(board), len(ranked))
    if not coverage["ok"]:
        log.warning("UK: unreviewed domains outrank the last board site: %s",
                    coverage["unreviewed_above_cutoff"])
    out_dir = config.SNAPSHOT_DIR / month
    snapshot.write_json(out_dir / "uk.json", snapshot.board_payload(
        board, "uk", month, radar.attribution(meta, "GB"), "cloudflare_radar", coverage))
    snapshot.write_ranked_csv(classified, out_dir / "uk_ranked_top100.csv", top_n=config.RADAR_LIMIT)
    log.info("UK top 5: %s", ", ".join(board["brand"].head(5)))
    return {"source": "cloudflare_radar"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Searchopoly board snapshots.")
    parser.add_argument("--month", help="Snapshot month as YYYY-MM (default: month of the Tranco list)")
    parser.add_argument("--board-size", type=int, default=config.BOARD_SIZE)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    rules = clean.load_rules()
    month, world_status = build_world(rules, args.month, args.board_size)
    uk_status = build_uk(rules, month, args.board_size)
    snapshot.write_latest_index(rules.categories, {"world": world_status, "uk": uk_status})
    return 0


if __name__ == "__main__":
    sys.exit(main())
