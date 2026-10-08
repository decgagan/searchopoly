"""Paths and tunable settings for the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DATA = ROOT / "pipeline" / "data"
SITE_MAP_CSV = PIPELINE_DATA / "site_map.csv"
EXCLUDE_CSV = PIPELINE_DATA / "exclude.csv"
CATEGORIES_CSV = PIPELINE_DATA / "categories.csv"

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
