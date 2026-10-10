"""'Most viewed people' board from English Wikipedia page views.

Steps for one month:

1. Exact monthly views for every English Wikipedia page come from Wikimedia's "pageview
   complete" monthly dump (user traffic only, so known crawlers and automated agents are
   already removed); see ``pipeline/pageview_dumps.py``. Non-articles (Main Page, Special:,
   Wikipedia:, File: and other namespaces) are dropped and the rest ranked.
2. Depth: every board starts from the month's top 5,000 articles (DEPTH_TIERS[0]). A colour
   set with fewer than 28 people there looks deeper, tier by tier (10,000, 20,000, 40,000),
   and only that set's board uses the deeper pool. The depth each set needed is recorded.
3. Titles are resolved to Wikidata items in batches, following redirects, so two titles for
   the same person merge (their exact monthly views are added together).
4. Humans only (Wikidata P31 = Q5), via the Wikidata Query Service. Fictional characters,
   events, films and so on drop out here.
5. Pages whose mobile share is implausible for English Wikipedia (5% or less, or 98% or
   more) are dropped as likely automated traffic, using the dump's desktop/mobile split.
6. Each person gets a colour set from their Wikidata occupations (see ``categorise``), with
   hand overrides in ``pipeline/data/people_overrides.csv``.

Only CC0 data is stored: view counts (Wikimedia), names, short descriptions, occupations and
dates (Wikidata). No Wikipedia article text and no images.
"""
from __future__ import annotations

import calendar
import json
import logging
import re
import time
from dataclasses import dataclass, field
from urllib.parse import quote

import pandas as pd
import requests

from . import config, pageview_dumps

log = logging.getLogger(__name__)

PROJECT = "en.wikipedia"
# Articles considered per month: every board starts at the first tier; a colour set short of
# 28 people moves to the next tier, and so on (only that set's board uses the deeper pool).
DEPTH_TIERS = (5_000, 10_000, 20_000, 40_000)
WIKI_API = "https://en.wikipedia.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"
BATCH = 50
HUMAN = "Q5"

# Namespaces that aren't articles (talk namespaces end in "talk", e.g. "User talk:").
NON_ARTICLE_NAMESPACES = {
    "special", "wikipedia", "file", "image", "portal", "help", "user", "category", "template",
    "draft", "module", "mediawiki", "timedtext", "book", "media", "talk", "project", "wp",
}
NON_ARTICLE_TITLES = {"main_page", "-", "undefined", "null"}

# Mobile share outside this range looks like automated traffic on English Wikipedia
# (normally about 60-75% of views are mobile). The low end is the classic bot signal: most
# automated traffic is desktop. The high end is lenient because real viral spikes, driven by
# social media on phones, can reach 95%+ mobile.
MOBILE_SHARE_MIN = 0.05
MOBILE_SHARE_MAX = 0.98

# Colour sets for people. Keys are the `group` the front end colours by.
PEOPLE_CATEGORIES = {
    "politics": "Politics",
    "royalty": "Royalty",
    "sport": "Sport",
    "music": "Music",
    "screen": "Film, TV & media",
    "business": "Business & tech",
    "other": "Other",
}

# Keyword rules matched against English occupation labels (lower case, whole words).
OCCUPATION_RULES = {
    "royalty": ["monarch", "royalty", "royal", "aristocrat", "nobleman", "noblewoman", "prince",
                "princess", "king", "queen", "emperor", "empress", "sovereign", "duke", "duchess",
                "consort", "regent"],
    "politics": ["politician", "diplomat", "statesperson", "statesman", "head of state",
                 "head of government", "president", "prime minister", "political", "senator",
                 "civil servant", "revolutionary", "military leader", "mayor"],
    "sport": ["player", "athlete", "footballer", "cricketer", "boxer", "wrestler", "racing driver",
              "golfer", "swimmer", "cyclist", "sprinter", "runner", "jockey", "martial artist",
              "formula one driver", "rally driver", "racecar driver", "motorcycle racer",
              "nascar driver", "racing automobile driver",
              "fighter", "skater", "skier", "gymnast", "tennis", "coach", "football manager",
              "association football manager", "sports manager", "sportsperson",
              "racer", "rugby", "chess player", "darts", "snooker", "basketball", "baseball",
              "bodybuilder", "referee"],
    "music": ["singer", "musician", "rapper", "songwriter", "composer", "guitarist", "drummer",
              "pianist", "bassist", "violinist", "disc jockey", "record producer", "music",
              "vocalist", "conductor", "keyboardist", "lyricist", "band"],
    "screen": ["actor", "actress", "film director", "director", "screenwriter", "film producer",
               "television presenter", "television personality", "presenter", "comedian",
               "voice actor", "youtuber", "streamer", "influencer", "television producer",
               "model", "journalist", "broadcaster", "podcaster", "talk show host",
               "internet celebrity", "content creator", "filmmaker", "cinematographer",
               "animator", "stunt performer"],
    "business": ["businessperson", "entrepreneur", "business executive", "executive",
                 "chief executive officer", "investor", "engineer", "computer scientist",
                 "programmer", "inventor", "industrialist", "banker", "venture capitalist",
                 "financier", "software developer", "technologist", "business magnate",
                 "philanthropist"],
}
# Ties between sets with the same number of matching occupations go to the earlier one.
TIE_ORDER = ["sport", "music", "screen", "business"]
# Below this share of a person's occupations, a set isn't a fair summary of them ("other").
MIN_SHARE = 0.25
# Exact occupation labels only: adult content is excluded, as on the website boards.
# (Mainstream actors and models with, say, "erotic photography model" are not excluded.)
EXCLUDED_OCCUPATIONS = {"pornographic actor", "pornographic film actor", "porn star",
                        "pornographic film director", "pornographic model", "camgirl"}


class PeopleUnavailable(RuntimeError):
    """The month's page-view data isn't published yet (or the API is down)."""


@dataclass
class Person:
    qid: str
    name: str
    description: str | None
    occupations: list[str] = field(default_factory=list)
    noble_title: bool = False
    died: str | None = None


# --- HTTP ---------------------------------------------------------------------------------

def _session() -> requests.Session:
    s = requests.Session()
    # Wikimedia's User-Agent policy: identify the tool and give a way to get in touch.
    s.headers["User-Agent"] = config.WIKIMEDIA_USER_AGENT
    s.headers["Api-User-Agent"] = config.WIKIMEDIA_USER_AGENT
    return s


def _get(session, url, retries=4, method="GET", **kw) -> requests.Response:
    for attempt in range(retries):
        try:
            res = session.request(method, url, timeout=config.HTTP_TIMEOUT, **kw)
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == retries - 1:
                raise
            log.info("Wikimedia: %s, retrying in %ds", type(exc).__name__, 5 * 2 ** attempt)
            time.sleep(5 * 2 ** attempt)
            continue
        if res.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            wait = float(res.headers.get("Retry-After") or 2 ** attempt)
            log.info("Wikimedia: HTTP %s, retrying in %.0fs", res.status_code, wait)
            time.sleep(wait)
            continue
        return res
    return res


def _cached_json(name: str, fetch):
    """Past months never change, so raw API answers are cached in .cache/."""
    path = config.CACHE_DIR / name
    if path.exists():
        return json.loads(path.read_text())
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


# --- Fetching -----------------------------------------------------------------------------

def top_articles(month: str, session=None, keep: int = DEPTH_TIERS[-1]) -> pd.DataFrame:
    """The month's top ``keep`` articles: rank (among articles), article, views, desktop."""
    try:
        # The dump's top 50,000 titles include a few thousand non-articles (Special:, File:...),
        # which still leaves more than the deepest tier's 40,000 articles.
        rows = pageview_dumps.monthly_top(month, session=session or _session())
    except pageview_dumps.DumpUnavailable as exc:
        raise PeopleUnavailable(str(exc)) from exc
    df = pd.DataFrame(rows, columns=["article", "views", "desktop"])
    df = df[df["article"].map(is_article)].head(keep).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


def is_article(title: str) -> bool:
    t = title.strip().lower()
    if not t or t in NON_ARTICLE_TITLES:
        return False
    if ":" in t:
        ns = t.split(":", 1)[0].replace("_", " ").strip()
        if ns in NON_ARTICLE_NAMESPACES or ns.endswith(" talk"):
            return False
    return True


def _load(name: str, default):
    path = config.CACHE_DIR / name
    return json.loads(path.read_text()) if path.exists() else default


def _save(name: str, data) -> None:
    path = config.CACHE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))


def resolve_qids(titles: list[str], session=None, month: str = "") -> dict[str, dict]:
    """Map each title to {'title': canonical title, 'qid': Wikidata id or None}.

    Follows redirects, so a redirect and its target resolve to the same item. Answers are
    cached per month and only new titles are looked up, so going a tier deeper is cheap.
    """
    session = session or _session()
    cache_name = f"wiki_qids_{month}.json"
    out = _load(cache_name, {}) if month else {}
    todo = [t for t in dict.fromkeys(titles) if t not in out]
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        res = _get(session, WIKI_API, params={
            "action": "query", "format": "json", "formatversion": 2, "redirects": 1,
            "prop": "pageprops", "ppprop": "wikibase_item", "titles": "|".join(batch),
        })
        res.raise_for_status()
        q = res.json().get("query", {})
        hop = {n["from"]: n["to"] for n in q.get("normalized", [])}
        hop.update({r["from"]: r["to"] for r in q.get("redirects", [])})
        pages = {p["title"]: p for p in q.get("pages", [])}
        for t in batch:
            cur, seen = t, set()
            while cur in hop and cur not in seen:
                seen.add(cur)
                cur = hop[cur]
            page = pages.get(cur, {})
            qid = (page.get("pageprops") or {}).get("wikibase_item")
            out[t] = {"title": cur.replace(" ", "_"), "qid": qid}
        if month and (i // BATCH) % 20 == 19:
            _save(cache_name, out)  # keep progress on long runs
    if month and todo:
        _save(cache_name, out)
    return {t: out[t] for t in titles if t in out}


HUMANS_ONLY = "SELECT ?item WHERE { VALUES ?item { %s } ?item wdt:P31 wd:Q5 . }"

# One row per human: occupations joined with "|", so the answer stays small.
SPARQL = """
SELECT ?item (SAMPLE(?lab) AS ?label) (SAMPLE(?desc) AS ?description)
       (GROUP_CONCAT(DISTINCT ?occLab; separator="|") AS ?occupations)
       (SAMPLE(?noble) AS ?nobleTitle) (MAX(?dod) AS ?died) (MAX(?prec) AS ?diedPrecision)
WHERE {
  VALUES ?item { %s }
  ?item wdt:P31 wd:Q5 .
  OPTIONAL { ?item rdfs:label ?labEn . FILTER(LANG(?labEn) = "en") }
  OPTIONAL { ?item rdfs:label ?labMul . FILTER(LANG(?labMul) = "mul") }
  BIND(COALESCE(?labEn, ?labMul) AS ?lab)
  OPTIONAL { ?item schema:description ?desc . FILTER(LANG(?desc) = "en") }
  OPTIONAL { ?item wdt:P106 ?occ . ?occ rdfs:label ?occLab . FILTER(LANG(?occLab) = "en") }
  OPTIONAL { ?item wdt:P97 ?noble . }
  OPTIONAL { ?item p:P570/psv:P570 [ wikibase:timeValue ?dod ; wikibase:timePrecision ?prec ] . }
}
GROUP BY ?item
"""


def fetch_humans(qids: list[str], session=None, month: str = "") -> dict[str, Person]:
    """Wikidata details for the items that are humans (instance of Q5); others are dropped.

    Two passes: a cheap "which of these are humans?" query in big batches, then the detailed
    query (labels, occupations, dates) for the humans only. Cached per month; only items not
    asked about before are queried, so going a tier deeper only costs the new items.
    """
    session = session or _session()
    qids = sorted(set(q for q in qids if q and re.fullmatch(r"Q\d+", q)))
    cache_name = f"wikidata_humans_v2_{month}.json"
    cache = _load(cache_name, {"queried": [], "rows": []}) if month else {"queried": [], "rows": []}
    asked = set(cache["queried"])
    todo = [q for q in qids if q not in asked]

    def sparql(query):
        res = _get(session, SPARQL_URL, method="POST", data={"query": query},
                   headers={"Accept": "application/sparql-results+json"})
        res.raise_for_status()
        time.sleep(0.5)  # be gentle with the query service
        return res.json()["results"]["bindings"]

    for i in range(0, len(todo), 1000):
        batch = todo[i:i + 1000]
        found = [r["item"]["value"].rsplit("/", 1)[-1]
                 for r in sparql(HUMANS_ONLY % " ".join(f"wd:{q}" for q in batch))]
        for j in range(0, len(found), 200):
            cache["rows"] += sparql(SPARQL % " ".join(f"wd:{q}" for q in found[j:j + 200]))
        cache["queried"] += batch
        if month:
            _save(cache_name, cache)
    wanted = set(qids)
    return {q: p for q, p in parse_humans(cache["rows"]).items() if q in wanted}


def parse_humans(rows: list[dict]) -> dict[str, Person]:
    """Parse grouped SPARQL rows (see SPARQL) into Person records keyed by QID."""
    val = lambda r, k: (r.get(k) or {}).get("value") or None
    people: dict[str, Person] = {}
    for r in rows:
        qid = val(r, "item").rsplit("/", 1)[-1]
        occupations = sorted(set(o for o in (val(r, "occupations") or "").split("|") if o))
        died = val(r, "died")
        people[qid] = Person(
            qid=qid,
            name=val(r, "label") or qid,
            description=val(r, "description"),
            occupations=occupations,
            noble_title=bool(val(r, "nobleTitle")),
            died=_date(died, val(r, "diedPrecision")) if died else None,
        )
    return people


def _date(value: str, precision) -> str:
    """Wikidata time to ISO: day precision -> YYYY-MM-DD, month -> YYYY-MM, else YYYY."""
    date = value.lstrip("+").split("T")[0]
    prec = int(precision) if precision else 11
    return date if prec >= 11 else date[:7] if prec == 10 else date[:4]


# --- Classification -----------------------------------------------------------------------

def _matches(label: str, keyword: str) -> bool:
    return re.search(rf"(^|\b){re.escape(keyword)}(\b|$)", label) is not None


# The Wikidata short description says what someone is known for ("English footballer",
# "President of the United States"), so it decides first: the earliest keyword in it wins.
# "other" words (writer, astronaut, activist...) only count when no named set matches, so
# "writer and comedian" is screen but "writer" alone is other.
DESCRIPTION_RULES = {
    "royalty": ["king", "queen", "prince", "princess", "emperor", "empress", "shah of", "consort",
                "monarch", "royal family", "duke", "duchess", "pharaoh", "khan of", "heir apparent",
                "noblewoman", "nobleman", "aristocrat", "countess", "earl", "peer", "ruler",
                "crown princess", "crown prince", "archduchess", "archduke", "sultan"],
    "politics": ["politician", "president of", "prime minister", "chief minister", "minister of",
                 "foreign minister", "governor", "senator", "mayor", "secretary of", "supreme leader",
                 "chancellor", "dictator", "head of state", "political", "congressman",
                 "congresswoman", "representative", "attorney general", "diplomat", "first lady",
                 "vice president", "director of the federal bureau", "speaker of", "statesman",
                 "politic"],
    "sport": ["footballer", "football player", "soccer player", "football manager", "football coach",
              "quarterback", "athlete", "skater", "skier", "swimmer", "boxer", "wrestler",
              "racing driver", "race car driver", "racecar driver", "formula one driver",
              "cricketer", "golfer", "sprinter", "gymnast", "jockey", "tennis player",
              "basketball player", "baseball player", "ice hockey player", "hockey player",
              "rugby", "cyclist", "snowboarder", "sportsperson", "mixed martial artist",
              "chess player", "darts player", "snooker player", "coach", "olympian",
              "head coach", "pitcher", "linebacker", "running back", "wide receiver", "sports executive"],
    "music": ["singer", "rapper", "musician", "songwriter", "band", "composer", "guitarist",
              "drummer", "pianist", "disc jockey", "record producer", "vocalist", "dj", "girl group",
              "boy band", "conductor"],
    "screen": ["actor", "actress", "filmmaker", "film director", "television director", "comedian",
               "presenter", "television", "youtuber", "streamer", "influencer", "model",
               "journalist", "broadcaster", "podcaster", "talk show host", "screenwriter",
               "film producer", "internet personality", "media personality", "reality"],
    "business": ["businessman", "businesswoman", "businessperson", "entrepreneur", "executive",
                 "investor", "ceo", "chief executive", "industrialist", "magnate", "billionaire",
                 "engineer", "computer scientist", "inventor", "financier", "banker",
                 "venture capitalist", "co-founder of", "programmer", "technologist", "tycoon"],
    "other": ["writer", "author", "novelist", "poet", "astronaut", "activist", "murderer",
              "serial killer", "killer", "criminal", "gangster", "drug lord", "terrorist",
              "hijacker", "cleric", "religious", "saint", "pope", "scientist", "physicist",
              "mathematician", "physician", "graffiti artist", "visual artist", "street artist", "painter", "designer", "photographer",
              "cartoonist", "philosopher", "historian", "socialite", "whistleblower", "linguist",
              "sex offender", "murder suspect", "prisoner", "mountaineer", "prophet", "theologian",
              "explorer", "psychologist", "economist", "chef", "aviator", "spiritual", "guru",
              "monk", "nun", "priest", "rabbi", "imam", "survivor", "victim", "spy"],
}


def describe_category(description: str | None) -> str | None:
    """Colour set from the Wikidata description: the earliest matching keyword wins."""
    text = (description or "").lower()
    best = None
    for cat, words in ((c, w) for c, w in DESCRIPTION_RULES.items() if c != "other"):
        for w in words:
            m = re.search(rf"\b{re.escape(w)}\b", text)
            if m and (best is None or m.start() < best[0] or (m.start() == best[0] and len(w) > best[2])):
                best = (m.start(), cat, len(w))
    if best:
        return best[1]
    if any(re.search(rf"\b{re.escape(w)}\b", text) for w in DESCRIPTION_RULES["other"]):
        return "other"
    return None


def categorise(person: Person, overrides: dict[str, str] | None = None) -> str:
    """Colour set: hand override, else the Wikidata description (``describe_category``),
    else Wikidata occupations as below.

    A royal occupation (monarch, duke...) and then politics win outright, because royals and
    politicians often list many other occupations. Otherwise the set with the most matching
    occupations wins, ties going to TIE_ORDER, as long as it covers at least MIN_SHARE of the
    person's occupations. A noble title alone (life peers, honorifics) only decides "royalty"
    when nothing else matches. Otherwise -> "other".
    """
    if overrides and person.qid in overrides:
        return overrides[person.qid]
    from_description = describe_category(person.description)
    if from_description:
        return from_description
    labels = [o.lower() for o in person.occupations]
    hits = {cat: sum(any(_matches(l, k) for k in kws) for l in labels)
            for cat, kws in OCCUPATION_RULES.items()}
    if hits["royalty"]:
        return "royalty"
    if hits["politics"]:
        return "politics"
    best = max(TIE_ORDER, key=lambda c: (hits[c], -TIE_ORDER.index(c)))
    if hits[best] and hits[best] >= MIN_SHARE * len(labels):
        return best
    return "royalty" if person.noble_title and not any(hits.values()) else "other"


ADULT_DESCRIPTION = re.compile(r"\b(porn\w*|adult film|adult entertainer|camgirl)\b", re.I)


def excluded_reason(person: Person) -> str | None:
    """Adult performers are left off, as adult sites are on the website boards.

    Only when it's what they're known for: an adult occupation *and* a Wikidata description
    that says so. Someone notable for something else keeps their place.
    """
    adult_job = any(o.lower() in EXCLUDED_OCCUPATIONS for o in person.occupations)
    if adult_job and ADULT_DESCRIPTION.search(person.description or ""):
        return "adult performer (adult content is excluded, as on the website boards)"
    return None


@dataclass
class Overrides:
    category: dict[str, str] = field(default_factory=dict)
    exclude: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)


def load_overrides(path=config.PEOPLE_OVERRIDES_CSV) -> Overrides:
    """Hand corrections keyed by QID."""
    if not path.exists():
        return Overrides()
    df = pd.read_csv(path, comment="#", skipinitialspace=True, dtype=str).fillna("")
    bad = sorted(set(df["category"]) - set(PEOPLE_CATEGORIES) - {""})
    if bad:
        raise ValueError(f"people_overrides.csv: unknown categories {bad}")
    if df["qid"].duplicated().any():
        raise ValueError(f"people_overrides.csv: duplicate QIDs {df['qid'][df['qid'].duplicated()].tolist()}")
    pick = lambda col: {r.qid: getattr(r, col) for r in df.itertuples() if getattr(r, col)}
    return Overrides(pick("category"), pick("exclude"), pick("description"))


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "person"


# --- Board --------------------------------------------------------------------------------

def build_people(top: pd.DataFrame, qids: dict[str, dict], humans: dict[str, Person],
                 mobile_share, board_size: int = config.BOARD_SIZE,
                 overrides: Overrides | None = None):
    """Rank people by views.

    Returns (board, category_boards, skipped):
      board            top ``board_size`` people overall
      category_boards  {category: top ``board_size`` people in that colour set}, from the whole
                       top-1,000 list, ranked 1..n inside the set (may be short: vacant lots)
      skipped          people who would have made a board but were left out, and why

    ``mobile_share(titles, views)`` gives the mobile share of a person's views; it's only
    called for people who could still make a board, to keep API calls down.
    """
    overrides = overrides or Overrides()
    rows: dict[str, dict] = {}
    for r in top.itertuples(index=False):
        if not is_article(r.article):
            continue
        info = qids.get(r.article) or {}
        qid = info.get("qid")
        if not qid or qid not in humans:
            continue
        row = rows.setdefault(qid, {"qid": qid, "views": 0, "source_rank": int(r.rank),
                                    "titles": [], "title": info["title"]})
        row["views"] += int(r.views)
        if r.article not in row["titles"]:
            row["titles"].append(r.article)
    ordered = sorted(rows.values(), key=lambda x: (-x["views"], x["source_rank"]))

    main: list[dict] = []
    by_cat: dict[str, list[dict]] = {c: [] for c in PEOPLE_CATEGORIES}
    skipped, used_ids = [], set(PEOPLE_CATEGORIES)  # a person id must never look like a set
    for row in ordered:
        person = humans[row["qid"]]
        category = categorise(person, overrides.category)
        if len(main) >= board_size and len(by_cat[category]) >= board_size:
            continue
        reason = overrides.exclude.get(person.qid) or excluded_reason(person)
        if not reason:
            share = mobile_share(row["titles"], row["views"])
            if share is not None and not (MOBILE_SHARE_MIN < share < MOBILE_SHARE_MAX):
                reason = f"likely automated traffic ({share:.0%} mobile)"
        if reason:
            skipped.append({"qid": person.qid, "name": person.name, "views": row["views"],
                            "category": category, "reason": reason})
            continue
        # Wikidata has no English or multilingual label for a few people: use the title.
        name = person.name if not re.fullmatch(r"Q\d+", person.name) else row["title"].replace("_", " ")
        pid = slug(name)
        if pid in used_ids:  # two people with the same name
            pid = f"{pid}-{person.qid.lower()}"
        used_ids.add(pid)
        entry = {
            "id": pid,
            "qid": person.qid,
            "name": name,
            "title": row["title"],
            "views": row["views"],
            "description": overrides.description.get(person.qid, person.description),
            "category": category,
            "died": person.died,
            "source_rank": row["source_rank"],
            "merged_titles": row["titles"] if len(row["titles"]) > 1 else None,
        }
        if len(main) < board_size:
            main.append(entry)
        if len(by_cat[category]) < board_size:
            by_cat[category].append(entry)

    def frame(entries):
        df = pd.DataFrame(entries, columns=["id", "qid", "name", "title", "views", "description",
                                            "category", "died", "source_rank", "merged_titles"])
        df.insert(0, "rank", range(1, len(df) + 1))
        return df

    return frame(main), {c: frame(e) for c, e in by_cat.items()}, skipped


def attribution(month: str) -> dict:
    y, m = month.split("-")
    return {
        "name": "Wikimedia Pageviews",
        "project": PROJECT,
        "access": "all-access",
        "agent": "user",
        "month": month,
        "url": f"https://pageviews.wmcloud.org/topviews/?project=en.wikipedia.org&platform=all-access&date={y}-{m}&excludes=",
        "dump": pageview_dumps.dump_url(month),
        "depth": DEPTH_TIERS[0],
        "licence": "Page views: CC0 1.0 (Wikimedia Foundation). Names, descriptions and occupations: Wikidata, CC0 1.0.",
    }


def build_tiered(top: pd.DataFrame, resolve, board_size: int = config.BOARD_SIZE,
                 overrides: Overrides | None = None, tiers=DEPTH_TIERS):
    """Build the boards, going deeper only for colour sets that are short of people.

    ``top`` has rank, article, views, desktop. ``resolve(titles)`` returns (qids, humans) for
    those titles. Returns (board, category_boards, skipped, depths) where depths[set] is the
    article depth that set's board drew on.

    Views are always summed over every resolved title, so a person's total is the same on
    every board they appear on.
    """
    desktop = dict(zip(top["article"], top["desktop"]))

    def mobile_share(titles, total):
        return 1 - sum(desktop.get(t, 0) for t in titles) / total if total else None

    depths, chosen, skipped_by_set = {}, {}, {}
    board = first_skipped = None
    for depth in tiers:
        pool = top.head(depth)
        titles = pool["article"].tolist()
        qids, humans = resolve(titles)
        b, cats, skipped = build_people(pool, qids, humans, mobile_share, board_size, overrides)
        if board is None:
            board, first_skipped = b, skipped
        for key, df in cats.items():
            if key not in chosen or len(chosen[key]) < board_size:
                chosen[key], depths[key] = df, depth
                skipped_by_set[key] = [s for s in skipped if s.get("category") == key]
        if all(len(df) >= board_size for df in chosen.values()) or len(top) <= depth:
            break
    # Main-board skips, plus anyone left off a deeper set board.
    seen = {s["qid"] for s in first_skipped}
    extra = [s for k in skipped_by_set for s in skipped_by_set[k]
             if depths[k] > tiers[0] and s["qid"] not in seen and not seen.add(s["qid"])]
    return board, chosen, first_skipped + extra, depths


def build_month(month: str, board_size: int = config.BOARD_SIZE, session=None):
    """Fetch and build one month. Returns (board, category_boards, skipped, source, depths)."""
    session = session or _session()
    top = top_articles(month, session)

    def resolve(titles):
        qids = resolve_qids(titles, session, month)
        humans = fetch_humans([v["qid"] for v in qids.values()], session, month)
        return qids, humans

    board, cats, skipped, depths = build_tiered(top, resolve, board_size, load_overrides())
    return board, cats, skipped, attribution(month), depths
