"""Streaming the Wikimedia page-view dump."""
import bz2

from pipeline import pageview_dumps as d

LINES = [
    b"de.wikipedia Berlin 1 desktop 999999 A1",
    b"en.wikibooks Cookbook 2 desktop 50 A1",
    b"en.wikipedia Alice 10 desktop 30 A1",
    b"en.wikipedia Alice 10 mobile-web 60 A1",
    b"en.wikipedia Alice 10 mobile-app 10 A1",
    b"en.wikipedia Bob 11 mobile-web 150 A1",
    b"en.wikipedia Carol 12 desktop 5 A1",
    b"en.wikipedia Dave_(musician) 13 desktop 120 A1",
    b"en.wikiquote Zed 3 desktop 999999 A1",   # past en.wikipedia: never read
]


def test_sums_access_methods_and_keeps_the_top():
    rows = d.top_titles(iter(LINES), keep=3)
    assert rows == [["Bob", 150, 0], ["Dave_(musician)", 120, 120], ["Alice", 100, 30]]


def test_stops_after_the_english_block():
    def lines():
        yield from LINES
        raise AssertionError("read past en.wikipedia")
    assert len(d.top_titles(lines(), keep=10)) == 4


def test_multistream_bzip2_is_read_to_the_end():
    blob = bz2.compress(b"\n".join(LINES[:4]) + b"\n") + bz2.compress(b"\n".join(LINES[4:]))
    chunks = [blob[i:i + 7] for i in range(0, len(blob), 7)]
    assert list(d._lines(chunks)) == LINES
