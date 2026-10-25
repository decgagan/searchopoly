"""Paths and tunable settings for the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DATA = ROOT / "pipeline" / "data"
SITE_MAP_CSV = PIPELINE_DATA / "site_map.csv"
EXCLUDE_CSV = PIPELINE_DATA / "exclude.csv"
CATEGORIES_CSV = PIPELINE_DATA / "categories.csv"
PEOPLE_OVERRIDES_CSV = PIPELINE_DATA / "people_overrides.csv"

OUTPUT_DIR = ROOT / "data"
SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"
LATEST_JSON = OUTPUT_DIR / "latest.json"

# Raw downloads live here and are git-ignored (the full Tranco list is ~1M rows).
CACHE_DIR = ROOT / ".cache"

# Squares on the board that hold a website.
BOARD_SIZE = 28

# How many raw ranked rows to publish as CSV for transparency.
RAW_TOP_N = 500

# How deep into the Tranco list to download. Tranco serves prefixes of any length,
# so we never need the full million rows.
TRANCO_FETCH_N = 5000

# Cloudflare Radar returns an ordered ranking for its top 100 domains only.
RADAR_LIMIT = 100

HTTP_TIMEOUT = 60
USER_AGENT = "Searchopoly-pipeline/0.1 (+https://github.com/decgagan/searchopoly)"
# Wikimedia's User-Agent policy asks for a tool name and a way to make contact.
WIKIMEDIA_USER_AGENT = ("Searchopoly-pipeline/0.7 (https://searchopoly.co.uk; "
                        "https://github.com/decgagan/searchopoly/issues) python-requests")

# Category boards: the top sites within each colour set. They reach deeper into the list
# than the main board, so every domain down to this raw rank must be reviewed (mapped or
# excluded) or the run flags it. A set with fewer sites than BOARD_SIZE in that depth gets
# "vacant lot" squares rather than padding from unreviewed domains.
CATEGORY_DEPTH = 1000

# URL slug -> colour-set group (pipeline/data/categories.csv) and label, in board order.
# Old slugs "search" and "tech" (before the two sets merged) redirect to "search-tech" in the site.
# The UK board has fewer real sites to draw on, so its filters merge the colour sets into
# three groups that can each fill 28 squares.
UK_CATEGORY_BOARDS = {
    "tech-work": (("search_tech", "work_money"), "Tech & work"),
    "social-entertainment": (("social_messaging", "entertainment"), "Social & entertainment"),
    "shopping-news": (("shopping", "news_sport", "reference_learning"), "Shopping, news & reference"),
}

CATEGORY_BOARDS = {
    "search-tech": ("search_tech", "Search & tech"),
    "social": ("social_messaging", "Social & messaging"),
    "entertainment": ("entertainment", "Entertainment"),
    "shopping": ("shopping", "Shopping"),
    "news": ("news_sport", "News & sport"),
    "reference": ("reference_learning", "Reference & learning"),
    "work": ("work_money", "Work & money"),
}
