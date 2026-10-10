"""Exact monthly page views for every English Wikipedia article, from Wikimedia's dumps.

The Pageviews API's top endpoint stops at 1,000 articles. Deeper rankings come from the
"pageview complete" monthly dump (https://dumps.wikimedia.org/other/pageview_complete/),
which lists every page of every wiki with its monthly views per access method, for user
traffic (the same agent type as the API's top lists). It is one bzip2 file per month,
about 6 GB, sorted by wiki and then title. We stream it, read only the ``en.wikipedia``
block (stopping as soon as it ends), add up each title's desktop, mobile-web and mobile-app
lines, and keep the top ``keep`` titles. Nothing is written to disk except that small
result, cached in .cache/ (past months never change).
"""
from __future__ import annotations

import bz2
import heapq
import json
import logging
import time

import requests

from . import config

log = logging.getLogger(__name__)

DUMP_URL = ("https://dumps.wikimedia.org/other/pageview_complete/monthly/{y}/{y}-{m:02d}/"
            "pageviews-{y}{m:02d}-user.bz2")
WIKI = b"en.wikipedia"
KEEP = 50_000
CHUNK = 1 << 20


class DumpUnavailable(RuntimeError):
    pass


def dump_url(month: str) -> str:
    y, m = map(int, month.split("-"))
    return DUMP_URL.format(y=y, m=m)


def _lines(chunks):
    """Decompress a (possibly multi-stream) bzip2 byte stream into lines."""
    dec = bz2.BZ2Decompressor()
    tail = b""
    for chunk in chunks:
        while chunk:
            data = dec.decompress(chunk)
            if dec.eof:  # next stream in a multi-stream file
                chunk = dec.unused_data
                dec = bz2.BZ2Decompressor()
            else:
                chunk = b""
            if data:
                parts = (tail + data).split(b"\n")
                tail = parts.pop()
                yield from parts
    if tail:
        yield tail


def top_titles(lines, keep: int = KEEP, wiki: bytes = WIKI):
    """Top ``keep`` titles by monthly views from dump lines, as [title, views, desktop] rows
    sorted by views. Stops reading once the wiki's block has passed."""
    prefix = wiki + b" "
    heap: list[tuple[int, int, str]] = []
    cur, total, desktop, seen = None, 0, 0, False

    def flush():
        if cur is None:
            return
        item = (total, desktop, cur)
        if len(heap) < keep:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)

    for line in lines:
        if not line.startswith(prefix):
            if seen:
                break  # sorted by wiki: we're past en.wikipedia
            continue
        seen = True
        parts = line.split(b" ")
        if len(parts) < 5:
            continue
        title, access, views = parts[1], parts[3], int(parts[4])
        if title != cur:
            flush()
            cur, total, desktop = title, 0, 0
        total += views
        if access == b"desktop":
            desktop += views
    flush()
    rows = sorted(heap, key=lambda x: (-x[0], x[2]))
    return [[t.decode("utf-8", "replace"), v, d] for v, d, t in rows]


def monthly_top(month: str, keep: int = KEEP, session: requests.Session | None = None) -> list[list]:
    """[title, views, desktop_views] for the month's top ``keep`` en.wikipedia titles (all
    namespaces; callers drop non-articles). Cached in .cache/."""
    path = config.CACHE_DIR / f"pageview_dump_top_{month}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if isinstance(cached, list):  # older cache format: a plain list of the top KEEP
            cached = {"keep": KEEP, "rows": cached}
        if cached["keep"] >= keep:
            return cached["rows"][:keep]
    session = session or requests.Session()
    session.headers["User-Agent"] = config.WIKIMEDIA_USER_AGENT  # Wikimedia blocks bare python-requests
    url = dump_url(month)
    started = time.time()
    with session.get(url, stream=True, timeout=config.HTTP_TIMEOUT) as res:
        if res.status_code == 404:
            raise DumpUnavailable(f"Wikimedia hasn't published the {month} page-view dump yet.")
        res.raise_for_status()
        rows = top_titles(_lines(res.iter_content(CHUNK)), keep)
    if not rows:
        raise DumpUnavailable(f"No {WIKI.decode()} rows in {url}.")
    log.info("Page-view dump %s: top %d titles in %.0fs", month, len(rows), time.time() - started)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"keep": keep, "rows": rows}, ensure_ascii=False, separators=(",", ":")))
    return rows
