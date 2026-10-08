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
        "category": "tech", "group": "tech_ai",
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
