# scraper/debug_fbref.py
import requests
from bs4 import BeautifulSoup, Comment
import json

URL = "https://fbref.com/en/comps/9/2024-2025/schedule/2024-2025-Premier-League-Scores-and-Fixtures"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_full_html(out_path="fbref_full.html"):
    print(f"🔍 Fetching: {URL}")
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(r.text)
    print(f"💾 Saved full HTML to {out_path} (len={len(r.text)})")
    return out_path

def extract_matches_from_table(table):
    matches = []
    tbody = table.find("tbody")
    if not tbody:
        return matches

    last_week = None

    for tr in tbody.find_all("tr"):
        # skip header/separator rows within tbody
        if "class" in tr.attrs and any(cls in ("thead", "over_header") for cls in tr["class"]):
            continue

        # pick cells by data-stat
        wk_el = tr.select_one('[data-stat="week"], [data-stat="round"]')
        home_el = tr.select_one('[data-stat="home_team"]')
        away_el = tr.select_one('[data-stat="away_team"]')
        report_a = tr.select_one('[data-stat="match_report"] a')

        # derive gameweek with carry-forward
        gw_text = wk_el.get_text(strip=True) if wk_el else ""
        if gw_text.isdigit():
            last_week = int(gw_text)
        gameweek = last_week

        if not (home_el and away_el):
            continue

        matches.append({
            "gameweek": gameweek,
            "home_team": home_el.get_text(strip=True),
            "away_team": away_el.get_text(strip=True),
            "match_report_url": report_a["href"] if report_a and report_a.get("href") else None,
        })

    return matches

def find_fixtures_in_html(html_path="fbref_full.html"):
    html = open(html_path, encoding="utf-8").read()
    soup = BeautifulSoup(html, "html.parser")

    # 1) Try direct tables first
    candidate_tables = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if any(h in headers for h in ("Wk", "Home", "Away", "Match Report")):
            candidate_tables.append(table)

    if candidate_tables:
        print(f"✅ Found {len(candidate_tables)} direct table(s) with expected headers.")
        return candidate_tables[0]

    # 2) FBref often wraps tables inside comments under div#all_*
    print("ℹ️  No direct table found. Scanning commented sections...")
    for c in soup.select('div[id^="all_"]'):
        for comment in c.find_all(string=lambda s: isinstance(s, Comment)):
            inner = BeautifulSoup(comment, "html.parser")
            table = inner.find("table")
            if not table:
                continue
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if any(h in headers for h in ("Wk", "Home", "Away", "Match Report")):
                print(f"✅ Found fixtures table inside commented container #{c.get('id')}")
                return table

    print("❌ Could not find fixtures table. Check file completeness or selectors.")
    return None

def main():
    full_path = fetch_full_html()
    table = find_fixtures_in_html(full_path)
    if not table:
        return

    # Save the located table HTML for inspection
    with open("fixtures_table.html", "w", encoding="utf-8") as f:
        f.write(str(table))
    print("💾 Saved fixtures table HTML to fixtures_table.html")

    matches = extract_matches_from_table(table)
    print(f"📊 Extracted rows: {len(matches)}")

    # Show first 5 samples
    for m in matches[:5]:
        print(m)

    # Save full JSON for inspection
    with open("fixtures_matches_debug.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    print("💾 Saved full matches JSON to fixtures_matches_debug.json")

if __name__ == "__main__":
    main()