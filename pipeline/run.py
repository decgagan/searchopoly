"""Run the whole pipeline.

    python -m pipeline.run                       # this month's snapshot
    python -m pipeline.run --month 2026-09       # a specific month
    python -m pipeline.run --backfill 2026-01:2026-10

Each month's World board uses the Tranco list dated the 1st of that month (covering the
previous 30 days), so months are comparable and every snapshot is reproducible from its list
ID. The UK board uses Cloudflare Radar (location=GB) for the same date; it needs
CLOUDFLARE_API_TOKEN and is skipped (marked pending) without it.

The People board (Wikipedia page views) needs a *complete* month, so it's built for each
requested month that has ended, and a plain run (no --month/--backfill) also builds the
previous month: the run on 3 November builds October's People board.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

from . import clean, config, crux, people, radar, report, snapshot, tranco

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
    categories = build_categories(classified, "world", month, source, "tranco", board_size)
    return report.BoardResult(
        "world", month, "ok", source=f"Tranco list {meta['list_id']} ({source['window']})",
        payload=payload, coverage=coverage, changed=changed,
        unreviewed=report.unreviewed_domains(classified),
        categories=categories,
    )


def build_categories(classified, board_name: str, month: str, source: dict, source_key: str,
                     board_size: int, depth: int = config.CATEGORY_DEPTH,
                     boards: dict | None = None) -> dict:
    """Per-colour-set boards from the same classified list, reaching CATEGORY_DEPTH deep."""
    groups = {k: g for k, (g, _) in (boards or config.CATEGORY_BOARDS).items()}
    boards = clean.build_category_boards(classified, groups, board_size, depth)
    coverage = {k: clean.category_coverage(classified, b, board_size, depth)
                for k, b in boards.items()}
    payload = snapshot.category_payload(boards, coverage, board_name, month, source, source_key,
                                        board_size, depth)
    changed = snapshot.write_json(config.SNAPSHOT_DIR / month / f"{board_name}_categories.json", payload,
                                 compact=True)
    return {"payload": payload, "changed": changed}


def _uk_pool(radar_ranked: pd.DataFrame, month: str) -> tuple[pd.DataFrame, dict, dict | None]:
    """Radar's ordered GB top 100, then CrUX's GB top-1,000 bucket for the month before.

    Radar stops at 100 domains, which leaves only about 20 real sites. CrUX lists the top 1,000
    origins Chrome users in the UK loaded, but without an order inside the bucket, so those
    domains are ordered by their world Tranco rank (the same list as the World board) and only
    fill the squares after the last Radar site. Returns the combined ranking (CrUX rows get
    ranks after Radar's), {combined rank: Tranco rank} for the CrUX rows, and the CrUX source.
    """
    crux_month = _month_before(month)
    try:
        bucket = crux.top_bucket(crux_month)
        world = tranco.download_list(tranco.list_meta(f"{month}-01"))
    except (crux.CruxUnavailable, tranco.TrancoUnavailable, requests.RequestException) as exc:
        log.warning("UK %s: no CrUX fill (%s)", month, exc)
        return radar_ranked, {}, None
    seen = set(radar_ranked["domain"].map(clean.normalise_domain))
    bucket["domain"] = bucket["domain"].map(clean.normalise_domain)
    bucket = bucket[~bucket["domain"].isin(seen)].drop_duplicates("domain")
    trank = dict(zip(world["domain"].map(clean.normalise_domain), world["rank"]))
    bucket["tranco_rank"] = bucket["domain"].map(trank)
    bucket = bucket.dropna(subset=["tranco_rank"]).sort_values("tranco_rank")
    base = int(radar_ranked["rank"].max())
    bucket["rank"] = range(base + 1, base + 1 + len(bucket))
    extra = dict(zip(bucket["rank"].astype(int), bucket["tranco_rank"].astype(int)))
    combined = pd.concat([radar_ranked, bucket[["rank", "domain"]]], ignore_index=True)
    return combined, extra, crux.attribution(crux_month)


def _mark_crux(sites: list[dict], extra: dict, crux_month: str | None) -> None:
    for s in sites:
        r = s.get("source_rank")
        if r in extra:
            s["source"] = "crux_gb"
            s["crux_month"] = crux_month
            s["tranco_rank"] = extra[r]


def build_uk(rules: clean.Rules, month: str, board_size: int) -> report.BoardResult:
    date = f"{month}-01"
    try:
        radar_ranked, meta = radar.fetch_top(location="GB", date=date)
    except radar.RadarUnavailable as exc:
        log.warning("UK board pending: %s", exc)
        return report.BoardResult("uk", month, "pending", message=str(exc))
    ranked, extra, crux_source = _uk_pool(radar_ranked, month)
    classified = clean.classify(ranked, rules)
    board = clean.build_board(classified, board_size)
    coverage = clean.coverage_check(classified, board)
    if len(board) < board_size:
        log.warning("UK: only %d user-facing sites", len(board))
    source = radar.attribution(meta, "GB")
    if crux_source:
        source["fill"] = crux_source
    payload = snapshot.board_payload(board, "uk", month, source, "cloudflare_radar", coverage)
    _mark_crux(payload["sites"], extra, crux_source and crux_source["month"])
    payload["radar_sites"] = sum(1 for s in payload["sites"] if s["source"] == "cloudflare_radar")
    out_dir = config.SNAPSHOT_DIR / month
    changed = snapshot.write_json(out_dir / "uk.json", payload)
    snapshot.write_ranked_csv(classified, out_dir / "uk_ranked.csv", top_n=len(ranked))
    depth = int(ranked["rank"].max())
    categories = build_categories(classified, "uk", month, source, "cloudflare_radar", board_size,
                                  depth=depth, boards=config.UK_CATEGORY_BOARDS)
    for b in categories["payload"]["boards"].values():
        _mark_crux(b["sites"], extra, crux_source and crux_source["month"])
    snapshot.write_json(out_dir / "uk_categories.json", categories["payload"], compact=True)
    return report.BoardResult(
        "uk", month, "ok", source=f"Cloudflare Radar GB top {len(radar_ranked)} ({source['list_date']})"
        + (f" + CrUX GB top 1,000 ({crux_source['month']})" if crux_source else ""),
        payload=payload, coverage=coverage, changed=changed,
        unreviewed=report.unreviewed_domains(classified, len(ranked)),
        categories=categories,
    )


def _month_before(month: str) -> str:
    y, m = map(int, month.split("-"))
    return f"{y - 1:04d}-12" if m == 1 else f"{y:04d}-{m - 1:02d}"


def people_months(months: list[str], today: str, include_previous: bool,
                  have=lambda m: True, catch_up: int = 3) -> list[str]:
    """Complete months (strictly before ``today``'s month) to build People boards for.

    A plain monthly run builds last month, plus any of the last ``catch_up`` complete months
    with no People board yet (``have(month)`` is False), e.g. if Wikimedia was late last time.
    """
    done = {m for m in months if m < today}
    if include_previous:
        prev = _month_before(today)
        done.add(prev)
        for _ in range(catch_up - 1):
            prev = _month_before(prev)
            if not have(prev):
                done.add(prev)
    return sorted(done)


def build_people(month: str, board_size: int) -> report.BoardResult:
    try:
        board, categories, skipped, source, depths = people.build_month(month, board_size)
    except people.PeopleUnavailable as exc:
        log.warning("People %s pending: %s", month, exc)
        return report.BoardResult("people", month, "pending", message=str(exc))
    except (requests.RequestException, OSError, EOFError) as exc:
        log.warning("People %s pending: Wikimedia request failed: %s", month, exc)
        return report.BoardResult("people", month, "pending", message=f"Wikimedia request failed ({exc}).")
    if len(board) < board_size:
        log.warning("People %s: only %d people found", month, len(board))
    payload = snapshot.people_payload(board, month, source, skipped)
    changed = snapshot.write_json(config.SNAPSHOT_DIR / month / "people.json", payload, compact=True)
    cats = snapshot.people_category_payload(categories, month, source, board_size, depths)
    cats_changed = snapshot.write_json(config.SNAPSHOT_DIR / month / "people_categories.json", cats,
                                       compact=True)
    return report.BoardResult("people", month, "ok", source=f"Wikimedia Pageviews, en.wikipedia, {month}",
                              payload=payload, changed=changed,
                              categories={"payload": cats, "changed": cats_changed})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Searchopoly board snapshots.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--month", help="Snapshot month as YYYY-MM (default: current month, UTC)")
    group.add_argument("--backfill", metavar="FROM:TO", help="Build every month in a range, oldest first")
    parser.add_argument("--board-size", type=int, default=config.BOARD_SIZE)
    parser.add_argument("--skip-people", action="store_true", help="Don't build People boards")
    args = parser.parse_args(argv)
    this_month = datetime.now(timezone.utc).strftime("%Y-%m")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.backfill:
        start, _, end = args.backfill.partition(":")
        if not (MONTH_RE.match(start) and MONTH_RE.match(end)) or start > end:
            parser.error("--backfill needs FROM:TO as YYYY-MM:YYYY-MM")
        months = month_range(start, end)
    else:
        month = args.month or this_month
        if not MONTH_RE.match(month):
            parser.error("--month needs YYYY-MM")
        months = [month]

    rules = clean.load_rules()
    results = []
    for month in months:  # oldest first, so movement is computed against the month before
        results.append(build_world(rules, month, args.board_size))
        results.append(build_uk(rules, month, args.board_size))
    if not args.skip_people:
        plain_run = not (args.month or args.backfill)
        have = lambda m: (config.SNAPSHOT_DIR / m / "people.json").exists()
        for month in people_months(months, this_month, include_previous=plain_run, have=have):
            results.append(build_people(month, args.board_size))

    last = {r.board: r for r in results}
    status = {
        b: ({"status": "pending", "reason": r.message.split(".")[0] + "."} if r.status == "pending" else {})
        for b, r in last.items()
    }
    curation = {
        "mapped_domains": int(len(rules.site_map)),
        "brands": int(rules.site_map["brand"].nunique()),
        "excluded_domains": int(len(rules.excludes)),
        "infra_patterns": len(clean.INFRA_PATTERNS),
    }
    snapshot.write_latest_index(rules.categories, status, curation)
    report.publish(results)

    failed = [r for r in results if r.board == "world" and r.status == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
