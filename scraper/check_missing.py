import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures_matches_debug.json"
RESULTS = ROOT / "all_matches_npxg.json"
MISSING_OUT = ROOT / "missing_fixtures.json"
BASE = "https://fbref.com"


def norm_url(u: str) -> str:
    if not u:
        return ""
    return (BASE + u) if u.startswith("/en/") else u

# Load fixtures (source of truth)
fixtures = json.loads(FIXTURES.read_text())
source_items = []
for i, f in enumerate(fixtures):
    url = norm_url(f.get("match_report_url") or "")
    if not url:
        continue
    source_items.append({
        "id": f"fixture_{i}",
        "home_team": f.get("home_team"),
        "away_team": f.get("away_team"),
        "url": url,
        "gameweek": f.get("gameweek"),
    })

source_urls = [x["url"] for x in source_items]
source_set = set(source_urls)

# Load extracted results
results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
result_urls = [norm_url(v.get("match_url") or "") for v in results.values() if v.get("match_url")]
result_urls = [u for u in result_urls if u]
result_set = set(result_urls)

# Compute differences / duplicates
missing_urls = sorted(source_set - result_set)
extra_urls = sorted(result_set - source_set)
url_counts = Counter(result_urls)
duplicates = sorted([u for u, c in url_counts.items() if c > 1])

# Build missing fixtures list preserving original fixture ids
missing_fixtures = [item for item in source_items if item["url"] in missing_urls]

# Write missing fixtures for re-run convenience
MISSING_OUT.write_text(json.dumps(missing_fixtures, indent=2))

print(f"Expected (non-null fixtures): {len(source_set)}")
print(f"Extracted:                  {len(result_set)}")
print(f"Missing:                    {len(missing_urls)}")
print(f"Extra:                      {len(extra_urls)}")
print(f"Duplicates:                 {len(duplicates)}\n")

if missing_urls:
    print("Missing URLs:")
    for u in missing_urls:
        print(u)

if duplicates:
    print("\nDuplicate URLs:")
    for u in duplicates:
        print(u)

if extra_urls:
    print("\nExtra URLs:")
    for u in extra_urls:
        print(u)