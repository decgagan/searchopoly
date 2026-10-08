import pandas as pd
import pytest

from pipeline import clean


@pytest.fixture
def rules():
    site_map = pd.DataFrame(
        [
            ("google.com", "Google", "google.com", "search"),
            ("google.co.uk", "Google", "google.com", "search"),
            ("youtube.com", "YouTube", "youtube.com", "video"),
            ("youtu.be", "YouTube", "youtube.com", "video"),
            ("bbc.co.uk", "BBC", "bbc.co.uk", "news"),
            ("cdnreviews.com", "CDN Reviews", "cdnreviews.com", "tech"),  # matches "cdn" pattern
            ("gov.uk", "GOV.UK", "gov.uk", "government"),
        ],
        columns=["domain", "brand", "canonical_domain", "category"],
    )
    excludes = pd.DataFrame(
        [("cloudflare.com", "infrastructure"), ("pornhub.com", "adult")],
        columns=["domain", "reason"],
    )
    categories = pd.DataFrame(
        [("search", "search_portals", "Search"), ("video", "entertainment", "Video"),
         ("news", "news_sport", "News"), ("tech", "tech_ai", "Tech"),
         ("government", "reference_learning", "Government")],
        columns=["category", "group", "label"],
    )
    clean.validate_rules(site_map, excludes, categories)
    return clean.Rules(site_map=site_map, excludes=excludes, categories=categories)


def ranking(*domains):
    return pd.DataFrame({"rank": range(1, len(domains) + 1), "domain": list(domains)})


def test_sibling_domains_merge_into_one_brand_with_best_rank(rules):
    raw = ranking("google.com", "youtube.com", "google.co.uk", "youtu.be")
    board = clean.build_board(clean.classify(raw, rules))
    assert board["brand"].tolist() == ["Google", "YouTube"]
    google = board.iloc[0]
    assert google["source_rank"] == 1
    assert google["domain"] == "google.com"
    assert set(google["merged_domains"]) == {"google.com", "google.co.uk"}


def test_infrastructure_domains_are_dropped(rules):
    raw = ranking("gstatic.com", "cloudflare.com", "akamaiedge.net", "googleapis.com",
                  "doubleclick.net", "amazonaws.com", "bbc.co.uk")
    classified = clean.classify(raw, rules)
    assert classified.loc[classified["domain"] != "bbc.co.uk", "status"].eq("excluded").all()
    board = clean.build_board(classified)
    assert board["brand"].tolist() == ["BBC"]
    assert board.iloc[0]["rank"] == 1


def test_adult_sites_never_reach_the_board(rules):
    raw = ranking("pornhub.com", "google.com")
    classified = clean.classify(raw, rules)
    assert classified.iloc[0]["status"] == "excluded"
    assert classified.iloc[0]["reason"] == "adult"
    assert "pornhub.com" not in sum(clean.build_board(classified)["merged_domains"], [])


def test_site_map_beats_infra_patterns(rules):
    classified = clean.classify(ranking("cdnreviews.com"), rules)
    assert classified.iloc[0]["status"] == "mapped"


def test_unknown_domains_are_unreviewed_and_flagged_by_coverage(rules):
    raw = ranking("google.com", "mystery-site.com", "bbc.co.uk")
    classified = clean.classify(raw, rules)
    board = clean.build_board(classified)
    assert board["brand"].tolist() == ["Google", "BBC"]
    cov = clean.coverage_check(classified, board)
    assert not cov["ok"]
    assert cov["unreviewed_above_cutoff"] == ["mystery-site.com"]
    assert cov["reviewed_through_rank"] == 1


def test_www_prefix_is_normalised(rules):
    classified = clean.classify(ranking("www.gov.uk", "WWW.BBC.CO.UK."), rules)
    assert classified["brand"].tolist() == ["GOV.UK", "BBC"]


def test_board_is_capped_and_ranked_contiguously(rules):
    raw = ranking("google.com", "youtube.com", "bbc.co.uk", "gov.uk")
    board = clean.build_board(clean.classify(raw, rules), board_size=3)
    assert board["rank"].tolist() == [1, 2, 3]


def test_validation_rejects_domain_in_both_lists(rules):
    bad_ex = pd.concat([rules.excludes, pd.DataFrame([("google.com", "oops")],
                                                     columns=["domain", "reason"])])
    with pytest.raises(ValueError, match="both site_map and exclude"):
        clean.validate_rules(rules.site_map, bad_ex, rules.categories)


def test_validation_rejects_brand_with_conflicting_categories(rules):
    bad_map = pd.concat([rules.site_map, pd.DataFrame(
        [("google.de", "Google", "google.com", "video")],
        columns=["domain", "brand", "canonical_domain", "category"])])
    with pytest.raises(ValueError, match="conflicting"):
        clean.validate_rules(bad_map, rules.excludes, rules.categories)


def test_brand_ids_are_url_safe_and_notes_carry_through(rules):
    rules.site_map["note"] = [None, "Includes country sites.", None, None, None, None, None]
    board = clean.build_board(clean.classify(ranking("google.com", "google.co.uk"), rules))
    assert board.iloc[0]["id"] == "google"
    assert board.iloc[0]["note"] == "Includes country sites."
    assert clean.slugify("X (Twitter)") == "x-twitter"
    assert clean.slugify("Yahoo! JAPAN") == "yahoo-japan"


def test_real_curation_files_are_valid():
    rules = clean.load_rules()  # raises on any problem
    assert len(rules.site_map) > 100
    assert (rules.excludes["reason"] == "adult").sum() >= 5


def test_snapshot_payload_is_strict_json(rules):
    import json
    from pipeline import snapshot
    rules.site_map["note"] = [None, None, "Has a note.", None, None, None, None]
    board = clean.build_board(clean.classify(ranking("google.com", "youtube.com"), rules))
    payload = snapshot.board_payload(board, "test", "2000-01", {}, "test", {})
    text = json.dumps(payload, allow_nan=False)  # raises on NaN
    sites = json.loads(text)["sites"]
    assert sites[0]["note"] is None and sites[1]["note"] == "Has a note."
