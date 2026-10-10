"""Category boards: the top sites within each colour set."""
import json
import re

import pandas as pd
import pytest

from pipeline import clean, config, snapshot

GROUPS = {"video": "entertainment", "news": "news_sport", "search": "search_tech"}


@pytest.fixture
def rules():
    site_map = pd.DataFrame(
        [
            ("google.com", "Google", "google.com", "search"),
            ("youtube.com", "YouTube", "youtube.com", "video"),
            ("youtu.be", "YouTube", "youtube.com", "video"),
            ("netflix.com", "Netflix", "netflix.com", "video"),
            ("spotify.com", "Spotify", "spotify.com", "music"),
            ("twitch.tv", "Twitch", "twitch.tv", "video"),
            ("bbc.co.uk", "BBC", "bbc.co.uk", "news"),
            ("cnn.com", "CNN", "cnn.com", "news"),
            ("espn.com", "ESPN", "espn.com", "sport"),
        ],
        columns=["domain", "brand", "canonical_domain", "category"],
    )
    excludes = pd.DataFrame([("cloudflare.com", "infrastructure")], columns=["domain", "reason"])
    categories = pd.DataFrame(
        [("search", "search_tech", "Search"), ("video", "entertainment", "Video"),
         ("music", "entertainment", "Music"), ("news", "news_sport", "News"),
         ("sport", "news_sport", "Sport")],
        columns=["category", "group", "label"],
    )
    clean.validate_rules(site_map, excludes, categories)
    return clean.Rules(site_map=site_map, excludes=excludes, categories=categories)


def ranking(*domains):
    return pd.DataFrame({"rank": range(1, len(domains) + 1), "domain": list(domains)})


def boards_for(rules, *domains, size=3, depth=1000):
    classified = clean.classify(ranking(*domains), rules)
    return classified, clean.build_category_boards(classified, GROUPS, size, depth)


def test_category_boards_rank_within_the_colour_set(rules):
    _, boards = boards_for(rules, "google.com", "cloudflare.com", "youtu.be", "bbc.co.uk",
                           "spotify.com", "youtube.com", "netflix.com", "espn.com")
    ent = boards["video"]
    # Video, music and gaming share a colour set; ranks restart at 1 inside it.
    assert ent["brand"].tolist() == ["YouTube", "Spotify", "Netflix"]
    assert ent["rank"].tolist() == [1, 2, 3]
    assert ent.iloc[0]["source_rank"] == 3  # best rank of youtu.be / youtube.com
    assert sorted(ent.iloc[0]["merged_domains"]) == ["youtu.be", "youtube.com"]
    assert boards["news"]["brand"].tolist() == ["BBC", "ESPN"]  # sport is in the same set
    assert boards["search"]["brand"].tolist() == ["Google"]


def test_category_boards_are_capped_and_respect_depth(rules):
    _, boards = boards_for(rules, "youtube.com", "netflix.com", "spotify.com", "twitch.tv",
                           "cnn.com", size=3, depth=4)
    assert len(boards["video"]) == 3            # capped at board size
    assert boards["news"].empty                 # cnn.com is at rank 5, deeper than depth 4


def test_full_category_board_only_needs_review_down_to_its_last_site(rules):
    classified, boards = boards_for(rules, "youtube.com", "netflix.com", "spotify.com",
                                    "mystery.com", size=3)
    cov = clean.category_coverage(classified, boards["video"], board_size=3, depth=1000)
    assert cov["ok"] and cov["cutoff_source_rank"] == 3


def test_short_category_board_must_be_reviewed_to_full_depth(rules):
    # Only one news site, so the board has vacant lots: that's only honest if nothing
    # unreviewed sits anywhere inside the depth.
    classified, boards = boards_for(rules, "bbc.co.uk", "youtube.com", "mystery.com", size=3)
    cov = clean.category_coverage(classified, boards["news"], board_size=3, depth=1000)
    assert not cov["ok"]
    assert cov["unreviewed_above_cutoff"] == ["mystery.com"]
    assert cov["cutoff_source_rank"] == 1000


def test_category_payload_movement_vacant_and_dropped_out(rules, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(config, "ROOT", tmp_path)

    def build(month, *domains):
        classified, boards = boards_for(rules, *domains, size=3)
        cov = {k: clean.category_coverage(classified, b, 3, 1000) for k, b in boards.items()}
        payload = snapshot.category_payload(boards, cov, "world", month, {}, "tranco", 3, 1000)
        snapshot.write_json(tmp_path / month / "world_categories.json", payload, compact=True)
        return payload

    first = build("2026-01", "youtube.com", "netflix.com", "twitch.tv", "bbc.co.uk")
    assert first["has_previous_month"] is False
    assert first["boards"]["news"]["vacant"] == 2
    assert first["brands"]["youtube"]["domain"] == "youtube.com"

    second = build("2026-02", "netflix.com", "youtube.com", "spotify.com", "bbc.co.uk")
    video = {s["id"]: s for s in second["boards"]["video"]["sites"]}
    assert second["has_previous_month"] is True
    assert video["netflix"]["movement"] == 1 and video["youtube"]["movement"] == -1
    assert video["spotify"]["previous_rank"] is None and video["spotify"]["movement"] is None
    assert second["boards"]["video"]["dropped_out"] == [
        {"id": "twitch", "brand": "Twitch", "previous_rank": 3}]
    # Every site on every board has its details in the shared brand table.
    ids = {s["id"] for b in second["boards"].values() for s in b["sites"]}
    assert ids == set(second["brands"])


def test_compact_json_round_trips_and_is_one_object_per_line(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    payload = {"generated_at": "x", "boards": {"a": {"sites": [{"rank": 1, "id": "a"},
                                                              {"rank": 2, "id": "b"}]}}}
    path = tmp_path / "c.json"
    snapshot.write_json(path, payload, compact=True)
    text = path.read_text()
    assert json.loads(text) == payload
    assert [l.strip() for l in text.splitlines()].count('{"rank":1,"id":"a"},') == 1
    assert snapshot.write_json(path, {**payload, "generated_at": "y"}, compact=True) is False


def test_category_board_slugs_cover_every_colour_set_once():
    rules = clean.load_rules()
    groups = [g for g, _ in config.CATEGORY_BOARDS.values()]
    assert sorted(groups) == sorted(rules.categories["group"].unique())
    # Slugs share the URL with brand ids (#world/shopping/amazon), so they mustn't clash.
    brand_ids = set(rules.site_map["brand"].map(clean.slugify))
    assert not (set(config.CATEGORY_BOARDS) & brand_ids)
    assert all(re.fullmatch(r"[a-z]+(-[a-z]+)*", s) for s in config.CATEGORY_BOARDS)


def test_published_category_boards_are_complete_and_fully_reviewed():
    index = json.loads(config.LATEST_JSON.read_text())
    months = index["category_boards"]["months"]["world"]
    assert months == index["boards"]["world"]["months"]
    for month in months:
        data = json.loads((config.SNAPSHOT_DIR / month / "world_categories.json").read_text())
        assert list(data["boards"]) == list(config.CATEGORY_BOARDS)
        for key, board in data["boards"].items():
            ranks = [s["rank"] for s in board["sites"]]
            assert ranks == list(range(1, len(ranks) + 1)), (month, key)
            assert len(ranks) + board["vacant"] == data["board_size"]
            assert board["coverage"]["ok"], (month, key, board["coverage"])
            group = config.CATEGORY_BOARDS[key][0]
            assert all(data["brands"][s["id"]]["group"] == group for s in board["sites"])
