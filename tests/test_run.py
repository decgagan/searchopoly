import json

import pandas as pd

from pipeline import config, report, run, snapshot


def test_month_range_crosses_year_end():
    assert run.month_range("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]


def _board(*brands):
    return pd.DataFrame({
        "rank": range(1, len(brands) + 1),
        "id": [b.lower() for b in brands],
        "brand": list(brands),
        "domain": [f"{b.lower()}.com" for b in brands],
        "category": "tech", "group": "search_tech",
        "source_rank": range(1, len(brands) + 1),
        "merged_domains": [[f"{b.lower()}.com"] for b in brands],
        "note": None,
    })


def test_movement_new_and_dropped_out(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    first = snapshot.board_payload(_board("A", "B", "C"), "world", "2026-01", {}, "t", {})
    assert first["has_previous_month"] is False
    snapshot.write_json(tmp_path / "2026-01" / "world.json", first)

    second = snapshot.board_payload(_board("C", "A", "D"), "world", "2026-02", {}, "t", {})
    sites = {s["brand"]: s for s in second["sites"]}
    assert second["has_previous_month"] is True
    assert sites["C"]["movement"] == 2 and sites["C"]["previous_rank"] == 3
    assert sites["A"]["movement"] == -1
    assert sites["D"]["previous_rank"] is None and sites["D"]["movement"] is None
    assert [d["brand"] for d in second["dropped_out"]] == ["B"]


def test_write_json_ignores_timestamp_only_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    path = tmp_path / "x.json"
    assert snapshot.write_json(path, {"generated_at": "1", "sites": [1]}) is True
    assert snapshot.write_json(path, {"generated_at": "2", "sites": [1]}) is False
    assert json.loads(path.read_text())["generated_at"] == "1"
    assert snapshot.write_json(path, {"generated_at": "3", "sites": [2]}) is True


def test_report_flags_unreviewed_domains(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    payload = {"sites": [{"brand": "A", "rank": 1}], "has_previous_month": False, "dropped_out": []}
    result = report.BoardResult(
        "world", "2026-10", "ok", source="Tranco list X", payload=payload,
        coverage={"reviewed_through_rank": 4, "last_board_source_rank": 30,
                  "unreviewed_above_cutoff": ["mystery.com"], "ok": False},
        unreviewed=[(5, "mystery.com"), (200, "other.com")],
    )
    pending = report.BoardResult("uk", "2026-10", "pending", message="No token.")
    text = report.publish([result, pending])
    assert "[!WARNING]" in text and "`mystery.com`" in text
    assert "2 unreviewed domains" in text
    assert "**Pending:** No token." in text
    assert summary.read_text() == text


def test_report_lists_category_boards_and_flags_gaps(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "s.md"))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    cats = {"changed": True, "payload": {
        "board_size": 28, "depth": 1000,
        "brands": {"google": {"brand": "Google"}},
        "boards": {
            "search-tech": {"sites": [{"id": "google", "rank": 1}], "vacant": 27,
                       "coverage": {"unreviewed_above_cutoff": ["mystery.com"], "ok": False}},
            "news": {"sites": [], "vacant": 28, "coverage": {"unreviewed_above_cutoff": ["mystery.com"]}},
        }}}
    result = report.BoardResult(
        "world", "2026-10", "ok", source="Tranco list X",
        payload={"sites": [{"brand": "Google", "rank": 1}], "has_previous_month": False, "dropped_out": []},
        coverage={"reviewed_through_rank": 999, "last_board_source_rank": 30,
                  "unreviewed_above_cutoff": [], "ok": True},
        categories=cats,
    )
    assert report.category_warnings(result) == ["mystery.com"]
    text = report.publish([result])
    assert "| Search & tech | 1 | 27 | 1,000 | Google |" in text
    assert "| News & sport | 0 | 28 | 1,000 | - |" in text
    assert "1 unreviewed domains rank inside the category-board depth" in text


def test_people_boards_only_for_complete_months():
    assert run.people_months(["2026-09", "2026-10"], "2026-10", include_previous=False) == ["2026-09"]
    # The plain monthly run on 3 November builds October's People board.
    assert run.people_months(["2026-11"], "2026-11", include_previous=True) == ["2026-10"]
    assert run.people_months(["2027-01"], "2027-01", include_previous=True) == ["2026-12"]


def test_plain_run_catches_up_on_missed_people_months():
    have = lambda m: m != "2026-09"  # Wikimedia was late in early October
    assert run.people_months(["2026-11"], "2026-11", True, have=have) == ["2026-09", "2026-10"]
