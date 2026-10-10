"""'Most viewed people' board from English Wikipedia page views.

Steps for one month:

1. Wikimedia Pageviews API: the month's top 1,000 en.wikipedia articles (all access methods,
   user agent only, so known crawlers and automated traffic are already removed).
2. Drop non-articles (Main Page, Special:, Wikipedia:, File: and other namespaces).
3. Resolve titles to Wikidata items in batches, following redirects, so two titles for the
   same person merge (their views are added together).
4. Keep humans only (Wikidata P31 = Q5) using one Wikidata Query Service request. Fictional
   characters, events, films and so on drop out here.
5. Drop pages whose mobile share is implausible for English Wikipedia (5% or less, or 98% or
   more): the mobile/desktop comparison Wikimedia's Topviews tool and Pageviews FAQ suggest
   for spotting automated traffic.
6. Give each person a colour set from their Wikidata occupations (see ``categorise``), with
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

from . import config

log = logging.getLogger(__name__)

PROJECT = "en.wikipedia"
TOP_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{project}/all-access/{y}/{m:02d}/all-days"
PER_ARTICLE_URL = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/"
                   "{access}/user/{title}/monthly/{start}/{end}")
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
        res = session.request(method, url, timeout=config.HTTP_TIMEOUT, **kw)
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

def top_articles(month: str, session=None) -> pd.DataFrame:
    """The month's top 1,000 articles as a DataFrame (rank, article, views)."""
    y, m = map(int, month.split("-"))
    url = TOP_URL.format(project=PROJECT, y=y, m=m)

    def fetch():
        res = _get(session or _session(), url)
        if res.status_code == 404:
            raise PeopleUnavailable(f"Wikimedia hasn't published page views for {month} yet.")
        if not res.ok:
            raise PeopleUnavailable(f"Wikimedia Pageviews API returned HTTP {res.status_code}.")
        return res.json()

    data = _cached_json(f"pageviews_top_{PROJECT}_{month}.json", fetch)
    articles = data["items"][0]["articles"]
    return pd.DataFrame(articles)[["rank", "article", "views"]]


def is_article(title: str) -> bool:
    t = title.strip().lower()
    if not t or t in NON_ARTICLE_TITLES:
        return False
    if ":" in t:
        ns = t.split(":", 1)[0].replace("_", " ").strip()
        if ns in NON_ARTICLE_NAMESPACES or ns.endswith(" talk"):
            return False
    return True


def resolve_qids(titles: list[str], session=None, month: str = "") -> dict[str, dict]:
    """Map each title to {'title': canonical title, 'qid': Wikidata id or None}.

    Follows redirects, so a redirect and its target resolve to the same item.
    """
    session = session or _session()

    def fetch():
        out = {}
        for i in range(0, len(titles), BATCH):
            batch = titles[i:i + BATCH]
            res = _get(session, WIKI_API, params={
                "action": "query", "format": "json", "formatversion": 2, "redirects": 1,
                "prop": "pageprops", "ppprop": "wikibase_item", "titles": "|".join(batch),
            })
            res.raise_for_status()
            q = res.json().get("query", {})
            hop = {}
            for n in q.get("normalized", []):
                hop[n["from"]] = n["to"]
            for r in q.get("redirects", []):
                hop[r["from"]] = r["to"]
            pages = {p["title"]: p for p in q.get("pages", [])}
            for t in batch:
                cur, seen = t, set()
                while cur in hop and cur not in seen:
                    seen.add(cur)
                    cur = hop[cur]
                page = pages.get(cur, {})
                qid = (page.get("pageprops") or {}).get("wikibase_item")
                out[t] = {"title": cur.replace(" ", "_"), "qid": qid}
        return out

    return _cached_json(f"wiki_qids_{month or 'adhoc'}.json", fetch) if month else fetch()


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
    """Wikidata details for the items that are humans (instance of Q5); others are dropped."""
    session = session or _session()
    qids = sorted(set(q for q in qids if q and re.fullmatch(r"Q\d+", q)))

    def fetch():
        rows = []
        for i in range(0, len(qids), 200):
            values = " ".join(f"wd:{q}" for q in qids[i:i + 200])
            res = _get(session, SPARQL_URL, method="POST", data={"query": SPARQL % values},
                       headers={"Accept": "application/sparql-results+json"})
            res.raise_for_status()
            rows += res.json()["results"]["bindings"]
            time.sleep(1)  # be gentle with the query service
        return rows

    rows = _cached_json(f"wikidata_humans_{month}.json", fetch) if month else fetch()
    return parse_humans(rows)


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


def desktop_views(title: str, month: str, session=None) -> int:
    y, m = map(int, month.split("-"))
    last = calendar.monthrange(y, m)[1]
    url = PER_ARTICLE_URL.format(project=PROJECT, access="desktop", title=quote(title, safe=""),
                                 start=f"{y}{m:02d}0100", end=f"{y}{m:02d}{last}00")
    res = _get(session or _session(), url)
    if res.status_code == 404:
        return 0
    res.raise_for_status()
    return sum(i["views"] for i in res.json().get("items", []))


# --- Classification -----------------------------------------------------------------------

def _matches(label: str, keyword: str) -> bool:
    return re.search(rf"(^|\b){re.escape(keyword)}(\b|$)", label) is not None


def categorise(person: Person, overrides: dict[str, str] | None = None) -> str:
    """Colour set from Wikidata occupations.

    A royal occupation (monarch, duke...) and then politics win outright, because royals and
    politicians often list many other occupations. Otherwise the set with the most matching
    occupations wins, ties going to TIE_ORDER, as long as it covers at least MIN_SHARE of the
    person's occupations. A noble title alone (life peers, honorifics) only decides "royalty"
    when nothing else matches. Otherwise -> "other".
    """
    if overrides and person.qid in overrides:
        return overrides[person.qid]
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
            skipped.append({"qid": person.qid, "name": person.name, "views": row["views"], "reason": reason})
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
        "api": TOP_URL.format(project=PROJECT, y=int(y), m=int(m)),
        "licence": "Page views: CC0 1.0 (Wikimedia Foundation). Names, descriptions and occupations: Wikidata, CC0 1.0.",
    }


def build_month(month: str, board_size: int = config.BOARD_SIZE, session=None):
    """Fetch and build one month. Returns (board, category_boards, skipped, source)."""
    session = session or _session()
    top = top_articles(month, session)
    titles = [t for t in top["article"] if is_article(t)]
    qids = resolve_qids(titles, session, month)
    humans = fetch_humans([v["qid"] for v in qids.values()], session, month)
    views_by_title = dict(zip(top["article"], top["views"]))
    share_cache_path = config.CACHE_DIR / f"pageviews_desktop_{month}.json"
    share_cache = json.loads(share_cache_path.read_text()) if share_cache_path.exists() else {}

    def mobile_share(titles, total):
        desktop = 0
        for t in titles:
            if t not in share_cache:
                share_cache[t] = desktop_views(t, month, session)
                time.sleep(0.05)
            desktop += share_cache[t]
        return 1 - desktop / total if total else None

    try:
        board, categories, skipped = build_people(top, qids, humans, mobile_share, board_size,
                                                  load_overrides())
    finally:
        share_cache_path.parent.mkdir(parents=True, exist_ok=True)
        share_cache_path.write_text(json.dumps(share_cache))
    return board, categories, skipped, attribution(month)
