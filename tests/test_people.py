"""People board: humans-only filter, duplicates, automated traffic and categories."""
import json

import pandas as pd
import pytest

from pipeline import config, people, snapshot
from pipeline.people import Overrides, Person


def P(qid, name, *occupations, noble=False, died=None, desc=None):
    return Person(qid=qid, name=name, description=desc, occupations=list(occupations),
                  noble_title=noble, died=died)


@pytest.mark.parametrize("title,ok", [
    ("Main_Page", False), ("Special:Search", False), ("Wikipedia:Featured_pictures", False),
    ("User_talk:Example", False), ("File:Cat.jpg", False), ("Category:Living_people", False),
    ("-", False), ("Taylor_Swift", True), ("Spider-Man:_Brand_New_Day", True),
    ("Monster:_The_Lizzie_Borden_Story", True), ("Deaths_in_2026", True),
])
def test_non_article_pages_are_dropped(title, ok):
    assert people.is_article(title) is ok


@pytest.mark.parametrize("person,expected", [
    (P("Q1", "Footballer", "association football player"), "sport"),
    (P("Q2", "Singer", "singer", "songwriter", "actor", "record producer"), "music"),
    (P("Q3", "Actor", "film actor", "television actor", "singer"), "screen"),
    (P("Q4", "President", "politician", "businessperson", "television presenter", "real estate developer", "entrepreneur"), "politics"),
    (P("Q5", "King", "monarch", "politician", noble=True), "royalty"),
    (P("Q6", "Duke", "duke", "naval officer", "helicopter pilot"), "royalty"),
    # A life peer's noble title doesn't make a politician royalty...
    (P("Q7", "Peer", "politician", noble=True), "politics"),
    # ...nor a pop star with a "King of Pop"-style title.
    (P("Q8", "Pop star", "singer", "dancer", "songwriter", "record producer", noble=True), "music"),
    (P("Q9", "CEO", "business executive", "general manager"), "business"),  # not sport
    # One stray match among many occupations isn't a fair summary.
    (P("Q10", "Photographer", "photographer", "environmentalist", "pianist", "writer", "university teacher"), "other"),
    (P("Q11", "Nobody", "prisoner"), "other"),
    (P("Q12", "Tie", "actor", "singer"), "music"),  # tie -> TIE_ORDER (music before screen)
])
def test_categorise_from_occupations(person, expected):
    assert people.categorise(person) == expected


def test_category_override_wins():
    assert people.categorise(P("Q1", "X", "singer"), {"Q1": "screen"}) == "screen"


def test_only_explicit_adult_occupations_are_excluded():
    assert people.excluded_reason(P("Q1", "X", "pornographic actor", desc="American pornographic actress"))
    assert people.excluded_reason(P("Q2", "Y", "film actor", "erotic photography model",
                                    desc="American actress")) is None
    # Notable for something else: stays, described neutrally by Wikidata.
    assert people.excluded_reason(P("Q3", "Z", "pornographic actor", "taxi driver",
                                    desc="British sex offender")) is None


def test_parse_grouped_sparql_rows():
    rows = [{
        "item": {"value": "http://www.wikidata.org/entity/Q42"},
        "label": {"value": "Douglas Adams"},
        "description": {"value": "English author and humourist (1952–2001)"},
        "occupations": {"value": "novelist|screenwriter|novelist"},
        "died": {"value": "2001-05-11T00:00:00Z"}, "diedPrecision": {"value": "11"},
    }, {
        "item": {"value": "http://www.wikidata.org/entity/Q7"},
        "occupations": {"value": ""}, "nobleTitle": {"value": "http://www.wikidata.org/entity/Q1"},
        "died": {"value": "1066-01-01T00:00:00Z"}, "diedPrecision": {"value": "9"},
    }]
    h = people.parse_humans(rows)
    assert h["Q42"].name == "Douglas Adams" and h["Q42"].occupations == ["novelist", "screenwriter"]
    assert h["Q42"].died == "2001-05-11"
    assert h["Q7"].name == "Q7" and h["Q7"].noble_title and h["Q7"].died == "1066"


def _top(*rows):
    return pd.DataFrame(rows, columns=["rank", "article", "views"])


def test_build_people_keeps_humans_merges_redirects_and_drops_bots():
    top = _top(
        (1, "Main_Page", 900), (2, "Special:Search", 800),
        (3, "Some_Film", 700),               # not a human
        (4, "Alice_Smith", 600),
        (5, "Bot_Target", 550),              # human, but 0% mobile
        (6, "Bob_Jones", 300),
        (7, "Alice_smith_(redirect)", 400),  # redirect to Alice: views add up
        (8, "Carol_Day", 200),
        (9, "Unknown_page", 100),            # no Wikidata item
    )
    qids = {
        "Some_Film": {"title": "Some_Film", "qid": "Q100"},
        "Alice_Smith": {"title": "Alice_Smith", "qid": "Q1"},
        "Alice_smith_(redirect)": {"title": "Alice_Smith", "qid": "Q1"},
        "Bot_Target": {"title": "Bot_Target", "qid": "Q9"},
        "Bob_Jones": {"title": "Bob_Jones", "qid": "Q2"},
        "Carol_Day": {"title": "Carol_Day", "qid": "Q3"},
        "Unknown_page": {"title": "Unknown_page", "qid": None},
    }
    humans = {
        "Q1": P("Q1", "Alice Smith", "singer"),
        "Q2": P("Q2", "Bob Jones", "politician", died="2026-03-01"),
        "Q3": P("Q3", "Carol Day", "tennis player"),
        "Q9": P("Q9", "Bot Target", "actor"),
    }
    shares = {"Bot_Target": 0.0}
    board, cats, skipped = people.build_people(
        top, qids, humans, lambda titles, views: shares.get(titles[0], 0.7), board_size=2)
    assert board["name"].tolist() == ["Alice Smith", "Bob Jones"]   # capped at 2
    # Category boards reach past the main board's cut-off and rank within the set.
    assert cats["sport"]["name"].tolist() == ["Carol Day"] and cats["sport"]["rank"].tolist() == [1]
    assert cats["screen"].empty                                     # Bot Target left out
    alice = board.iloc[0]
    assert alice["views"] == 1000 and alice["source_rank"] == 4
    assert alice["merged_titles"] == ["Alice_Smith", "Alice_smith_(redirect)"]
    assert board.iloc[1]["died"] == "2026-03-01" and board.iloc[1]["category"] == "politics"
    assert skipped == [{"qid": "Q9", "name": "Bot Target", "views": 550, "category": "screen",
                        "reason": "likely automated traffic (0% mobile)"}]


def test_overrides_exclude_and_fix_descriptions():
    top = _top((1, "A", 10), (2, "B", 5))
    qids = {"A": {"title": "A", "qid": "Q1"}, "B": {"title": "B", "qid": "Q2"}}
    humans = {"Q1": P("Q1", "A", "singer"), "Q2": P("Q2", "B", "singer", desc="wrong")}
    ov = Overrides(exclude={"Q1": "test"}, description={"Q2": "right"})
    board, _, skipped = people.build_people(top, qids, humans, lambda t, v: 0.7, 28, ov)
    assert board["name"].tolist() == ["B"] and board.iloc[0]["description"] == "right"
    assert skipped[0]["reason"] == "test"


def test_people_payload_movement_and_strict_json(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(config, "ROOT", tmp_path)

    def board(*names):
        return pd.DataFrame([{
            "rank": i + 1, "id": n.lower(), "qid": f"Q{i}", "name": n, "title": n,
            "views": 100 - i, "description": None, "category": "other", "died": None,
            "source_rank": i + 3, "merged_titles": None} for i, n in enumerate(names)])

    first = snapshot.people_payload(board("A", "B"), "2026-01", {"name": "x"}, [])
    snapshot.write_json(tmp_path / "2026-01" / "people.json", first, compact=True)
    second = snapshot.people_payload(board("B", "C"), "2026-02", {"name": "x"}, [])
    sites = {s["id"]: s for s in second["sites"]}
    assert sites["b"]["movement"] == 1 and sites["c"]["previous_rank"] is None
    assert [d["name"] for d in second["dropped_out"]] == ["A"]
    json.dumps(second, allow_nan=False)               # no NaN sneaking in from pandas
    assert "description" not in sites["b"] and "died" not in sites["b"]  # empty fields left out


def test_real_people_overrides_file_is_valid():
    ov = people.load_overrides()
    assert set(ov.category.values()) <= set(people.PEOPLE_CATEGORIES)


def test_person_ids_never_clash_with_colour_set_slugs():
    top = _top((1, "Music_(rapper)", 10))
    qids = {"Music_(rapper)": {"title": "Music_(rapper)", "qid": "Q1"}}
    board, _, _ = people.build_people(top, qids, {"Q1": P("Q1", "Music", "rapper")}, lambda t, v: 0.7)
    assert board.iloc[0]["id"] == "music-q1"


def test_people_category_payload_shares_people_and_tracks_movement(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(config, "ROOT", tmp_path)

    def cat_board(*names):
        return pd.DataFrame([{
            "rank": i + 1, "id": n.lower(), "qid": f"Q{n}", "name": n, "title": n, "views": 9 - i,
            "description": None, "category": "sport", "died": None, "source_rank": i + 1,
            "merged_titles": None} for i, n in enumerate(names)])

    first = snapshot.people_category_payload({"sport": cat_board("A", "B"), "music": cat_board()},
                                             "2026-01", {}, board_size=3)
    snapshot.write_json(tmp_path / "2026-01" / "people_categories.json", first, compact=True)
    second = snapshot.people_category_payload({"sport": cat_board("B", "C"), "music": cat_board()},
                                              "2026-02", {}, board_size=3)
    sport = second["boards"]["sport"]
    assert sport["vacant"] == 1 and second["boards"]["music"]["vacant"] == 3
    assert sport["sites"][0] == {"rank": 1, "id": "b", "previous_rank": 2, "movement": 1}
    assert sport["dropped_out"] == [{"id": "a", "name": "A", "previous_rank": 1}]
    assert set(second["brands"]) == {"b", "c"} and second["brands"]["b"]["name"] == "B"


def test_tiers_go_deeper_only_for_short_sets():
    # 4 articles: two singers near the top, one royal only in the deeper tier, one bot.
    top = pd.DataFrame([
        (1, "Singer_A", 900, 300), (2, "Singer_B", 800, 300), (3, "Bot_Royal", 700, 700),
        (4, "Royal_C", 50, 20),
    ], columns=["rank", "article", "views", "desktop"])
    humans = {"Q1": P("Q1", "Singer A", "singer"), "Q2": P("Q2", "Singer B", "singer"),
              "Q3": P("Q3", "Bot Royal", "monarch"), "Q4": P("Q4", "Royal C", "monarch")}
    asked = []

    def resolve(titles):
        asked.append(len(titles))
        q = {t: {"title": t, "qid": f"Q{i + 1}"} for i, t in enumerate(top["article"]) if t in titles}
        return q, {v["qid"]: humans[v["qid"]] for v in q.values()}

    board, cats, skipped, depths = people.build_tiered(top, resolve, board_size=1, tiers=(3, 4, 10))
    assert asked == [3, 4]                       # stopped once every set was full or the list ran out
    assert board["name"].tolist() == ["Singer A"]
    assert depths["music"] == 3 and cats["music"]["name"].tolist() == ["Singer A"]
    assert depths["royalty"] == 4 and cats["royalty"]["name"].tolist() == ["Royal C"]
    assert [s["name"] for s in skipped] == ["Bot Royal"]   # 100% desktop, listed once
    assert cats["royalty"].iloc[0]["source_rank"] == 4


@pytest.mark.parametrize("description,expected", [
    ("English footballer (born 1975)", "sport"),
    ("President of the United States (2017–2021; since 2025)", "politics"),
    ("United States Secretary of the Treasury", "politics"),
    ("president and co-founder of Anthropic", "business"),      # "president of" only
    ("American attorney and sixth director of the FBI", None),   # not a film director
    ("Hong Kong–American martial artist and actor", "screen"),   # "artist" isn't a set word
    ("American writer and political aide", "politics"),          # named sets beat "other" words
    ("American writer (born 1972)", "other"),
    ("American astronaut (born 1979)", "other"),
    ("member of the British royal family and Princess of Wales", "royalty"),
    ("Australian-American actress, producer, and model", "screen"),
    ("Brazilian racing driver (1960–1994)", "sport"),
    ("", None), (None, None),
])
def test_description_decides_first(description, expected):
    assert people.describe_category(description) == expected


def test_description_beats_a_stray_occupation():
    pele = P("Q12897", "Pelé", "association football player", "politician", desc="Brazilian footballer (1940–2022)")
    assert people.categorise(pele) == "sport"          # occupations alone would say politics
    assert people.categorise(P("Q1", "X", "politician", desc="no keywords here")) == "politics"


def test_crime_occupations_never_land_in_a_field():
    p = P("Q1317", "Osama bin Laden", "businessperson", "civil engineer", "terrorist",
          desc="founder of al-Qaeda (1957–2011)")
    assert people.categorise(p) == "other"
