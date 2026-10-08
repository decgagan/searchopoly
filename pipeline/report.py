"""Human-readable run report: what was built, who moved, and which domains need curating.

Printed to the log every run. In GitHub Actions it's also written to the job summary
($GITHUB_STEP_SUMMARY) and blocking issues become workflow warnings.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import pandas as pd

from . import config

log = logging.getLogger(__name__)

MAX_UNREVIEWED_LISTED = 25


@dataclass
class BoardResult:
    board: str
    month: str
    status: str                       # "ok", "pending" or "failed"
    source: str = ""
    message: str = ""
    payload: dict | None = None
    coverage: dict | None = None
    unreviewed: list[tuple[int, str]] = field(default_factory=list)
    changed: bool = False


def unreviewed_domains(classified: pd.DataFrame, top_n: int = config.RAW_TOP_N) -> list[tuple[int, str]]:
    rows = classified[(classified["status"] == "unreviewed") & (classified["rank"] <= top_n)]
    return [(int(r), d) for r, d in zip(rows["rank"], rows["domain"])]


def _movers(payload: dict) -> str:
    if not payload.get("has_previous_month"):
        return "First month on record, so no movement yet."
    sites = payload["sites"]
    moved = [s for s in sites if s.get("movement")]
    new = [s["brand"] for s in sites if s.get("previous_rank") is None]
    out = [s["brand"] for s in payload.get("dropped_out", [])]
    parts = []
    if moved:
        up = max(moved, key=lambda s: s["movement"])
        down = min(moved, key=lambda s: s["movement"])
        if up["movement"] > 0:
            parts.append(f"biggest climber **{up['brand']}** (+{up['movement']})")
        if down["movement"] < 0:
            parts.append(f"biggest faller **{down['brand']}** ({down['movement']})")
    if new:
        parts.append("new: " + ", ".join(new))
    if out:
        parts.append("dropped out: " + ", ".join(out))
    text = "; ".join(parts) or "no changes in the top positions."
    return text[0].upper() + text[1:]


def render(results: list[BoardResult]) -> str:
    lines = ["# Searchopoly pipeline run", ""]
    for r in results:
        title = f"## {r.board.upper()} · {r.month}"
        if r.status != "ok":
            lines += [title, "", f"**{r.status.title()}:** {r.message}", ""]
            continue
        top = ", ".join(s["brand"] for s in r.payload["sites"][:5])
        lines += [
            title, "",
            f"- Source: {r.source}",
            f"- File: {'updated' if r.changed else 'unchanged'}",
            f"- Top 5: {top}",
            f"- Movement: {_movers(r.payload)}",
            f"- Reviewed through raw rank {r.coverage['reviewed_through_rank']} "
            f"(28th board site is at raw rank {r.coverage['last_board_source_rank']})",
            "",
        ]
        if r.coverage["unreviewed_above_cutoff"]:
            lines += [
                "> [!WARNING]",
                "> These unreviewed domains rank above the last board site, so a real site may be "
                "missing from the board. Add each to `pipeline/data/site_map.csv` or `exclude.csv`: "
                + ", ".join(f"`{d}`" for d in r.coverage["unreviewed_above_cutoff"]),
                "",
            ]
        if r.unreviewed:
            shown = r.unreviewed[:MAX_UNREVIEWED_LISTED]
            lines += [
                f"<details><summary>{len(r.unreviewed)} unreviewed domains in the raw top "
                f"{config.RAW_TOP_N}</summary>", "",
                "| Raw rank | Domain |", "|---:|---|",
                *[f"| {rank} | `{d}` |" for rank, d in shown],
            ]
            if len(r.unreviewed) > len(shown):
                lines.append(f"| … | {len(r.unreviewed) - len(shown)} more in the ranked CSV |")
            lines += ["", "</details>", ""]
    return "\n".join(lines) + "\n"


def publish(results: list[BoardResult]) -> str:
    text = render(results)
    log.info("Run report:\n%s", text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for r in results:
            if r.coverage and r.coverage["unreviewed_above_cutoff"]:
                domains = ", ".join(r.coverage["unreviewed_above_cutoff"])
                print(f"::warning title=Searchopoly {r.board} {r.month}: domains to review::{domains}")
            if r.status == "failed":
                print(f"::error title=Searchopoly {r.board} {r.month}::{r.message}")
    return text
