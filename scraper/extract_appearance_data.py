import json
import os
import random
import re
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup, Comment

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), 'fixtures_matches_debug.json')
OUTPUT_JSONL = os.path.join(os.path.dirname(__file__), 'appearance_data.jsonl')
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), 'appearance_data.json')
FAIL_LOG = os.path.join(os.path.dirname(__file__), 'appearance_failures.log')
BASE_URL = 'https://fbref.com'

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
]

RANDOM_DELAY_RANGE_SECONDS = (2.0, 5.0)
MAX_RETRIES_PER_URL = 3
BATCH_SIZE = 10
BATCH_COOLDOWN_SECONDS = 20
CONSECUTIVE_FAIL_CUTOFF = 5


@dataclass
class AppearanceRow:
    matchId: str
    matchUrl: str
    playerName: str
    teamName: str
    in_squad: bool
    started: bool
    minutes_played: Optional[int]
    npXg: Optional[float]
    xAG: Optional[float]


def load_fixtures() -> List[Dict]:
    with open(FIXTURES_PATH, 'r', encoding='utf-8') as f:
        fixtures = json.load(f)
    # normalize shape: support list of dicts keyed fixture_i too
    if isinstance(fixtures, dict):
        # convert to list
        out: List[Dict] = []
        for key, value in fixtures.items():
            if isinstance(value, dict):
                out.append(value)
        fixtures = out
    return fixtures


def to_abs_url(url: str) -> str:
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('/'):
        return BASE_URL + url
    return BASE_URL + '/' + url


def request_html(url: str) -> Optional[str]:
    for attempt in range(1, MAX_RETRIES_PER_URL + 1):
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Referer': 'https://www.google.com/',
            }
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code == 200 and resp.text:
                return resp.text
            time.sleep(random.uniform(1.0, 2.0))
        except Exception:
            time.sleep(random.uniform(1.0, 2.0))
    return None


def parse_minutes(raw: str) -> Optional[int]:
    if not raw:
        return None
    try:
        return int(raw)
    except Exception:
        # Some rows might be like '90+2'
        match = re.match(r'^(\d+)', raw)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
        return None


def parse_float(raw: str) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip()
    if s == '' or s == '-':
        return None
    try:
        return float(s)
    except Exception:
        # Sometimes comma decimal or stray chars
        s = s.replace(',', '')
        try:
            return float(s)
        except Exception:
            return None


def extract_player_rows_from_table(table: BeautifulSoup, team_name_from_caption: str, match_id: str, match_url: str) -> List[AppearanceRow]:
    rows: List[AppearanceRow] = []

    # Determine started/bench by position relative to a header row containing 'Bench'
    started_flag = True

    tbody = table.find('tbody')
    if not tbody:
        return rows

    for tr in tbody.find_all('tr', recursive=False):
        # Header breaks such as 'Bench'
        if 'class' in tr.attrs and 'thead' in tr['class']:
            txt = tr.get_text(strip=True)
            if 'Bench' in txt:
                started_flag = False
            continue

        # Skip separator rows
        if tr.get('data-row') == '0' and 'min' in tr.get_text().lower() and 'player' in tr.get_text().lower():
            continue

        player_cell = tr.find('th', attrs={'data-stat': 'player'})
        if not player_cell:
            # Some tables use td for player too
            player_cell = tr.find('td', attrs={'data-stat': 'player'})
        if not player_cell:
            continue

        player_name = player_cell.get_text(strip=True)
        if not player_name:
            continue

        minutes_cell = tr.find('td', attrs={'data-stat': 'minutes'})
        npxg_cell = tr.find('td', attrs={'data-stat': 'npxg'})
        xa_cell = tr.find('td', attrs={'data-stat': 'xg_assist'})

        minutes_val = parse_minutes(minutes_cell.get_text(strip=True) if minutes_cell else '')
        npxg_val = parse_float(npxg_cell.get_text(strip=True) if npxg_cell else None)
        xa_val = parse_float(xa_cell.get_text(strip=True) if xa_cell else None)

        rows.append(
            AppearanceRow(
                matchId=match_id,
                matchUrl=match_url,
                playerName=player_name,
                teamName=team_name_from_caption,
                in_squad=True,  # Appears in player stats => considered in matchday squad
                started=started_flag,
                minutes_played=minutes_val,
                npXg=npxg_val,
                xAG=xa_val,
            )
        )

    return rows


def extract_unused_subs_from_lineups(soup: BeautifulSoup, played_players: Set[str], match_id: str, match_url: str) -> List[AppearanceRow]:
    """Parse the lineup sections to find bench players who did NOT appear (unused subs).
    We only add rows for bench players not present in played_players.
    """
    results: List[AppearanceRow] = []

    for lineup_div in soup.find_all('div', class_='lineup'):
        table = lineup_div.find('table')
        if not table:
            continue

        # Team name from first header row, without formation suffix in parentheses
        first_th = table.find('th')
        if not first_th:
            continue
        team_header = first_th.get_text(strip=True)
        team_name = team_header.split('(')[0].strip()

        seen_bench = False
        for tr in table.find_all('tr'):
            th = tr.find('th')
            if th and 'Bench' in th.get_text(strip=True):
                seen_bench = True
                continue
            if not seen_bench:
                continue
            # bench row: second td has player link
            tds = tr.find_all('td')
            if len(tds) < 2:
                continue
            player_link = tds[1].find('a')
            player_name = player_link.get_text(strip=True) if player_link else tds[1].get_text(strip=True)
            if not player_name:
                continue
            if player_name in played_players:
                # This bench player actually appeared; skip to avoid duplicate
                continue
            results.append(
                AppearanceRow(
                    matchId=match_id,
                    matchUrl=match_url,
                    playerName=player_name,
                    teamName=team_name,
                    in_squad=True,
                    started=False,
                    minutes_played=None,
                    npXg=None,
                    xAG=None,
                )
            )

    return results


def get_lineup_starters(soup: BeautifulSoup) -> Set[str]:
    starters: Set[str] = set()
    for lineup_div in soup.find_all('div', class_='lineup'):
        table = lineup_div.find('table')
        if not table:
            continue
        seen_bench = False
        for tr in table.find_all('tr'):
            th = tr.find('th')
            if th and 'Bench' in th.get_text(strip=True):
                seen_bench = True
                break
            # within starters area, the second td contains player link/name
            tds = tr.find_all('td')
            if len(tds) < 2:
                continue
            a = tds[1].find('a')
            name = a.get_text(strip=True) if a else tds[1].get_text(strip=True)
            if name:
                starters.add(name)
    return starters


def extract_from_html(html: str, match_url: str) -> List[AppearanceRow]:
    """Parses a single match report HTML and returns all AppearanceRow for both teams.
    Handles FBref's commented tables by parsing comments that contain tables with ids like 'stats_*_summary'.
    Adds bench-but-did-not-play players by parsing lineup sections.
    """
    results: List[AppearanceRow] = []

    soup = BeautifulSoup(html, 'html.parser')

    # Collect all candidate tables from both live DOM and commented HTML
    candidate_tables: List[BeautifulSoup] = []

    # 1) Direct tables if present
    for tbl in soup.find_all('table'):
        table_id = tbl.get('id', '')
        if table_id.startswith('stats_') and table_id.endswith('_summary'):
            candidate_tables.append(tbl)

    # 2) Commented tables
    for c in soup.find_all(string=lambda text: isinstance(text, Comment)):
        text = str(c)
        if 'table' not in text or 'stats_' not in text:
            continue
        try:
            sub_soup = BeautifulSoup(text, 'html.parser')
            for tbl in sub_soup.find_all('table'):
                table_id = tbl.get('id', '')
                if table_id.startswith('stats_') and table_id.endswith('_summary'):
                    candidate_tables.append(tbl)
        except Exception:
            continue

    # For each table, identify the team name from caption like "<Team> Player Stats"
    played_players: Set[str] = set()
    starters_from_lineup: Set[str] = get_lineup_starters(soup)
    for tbl in candidate_tables:
        caption_el = tbl.find('caption')
        if not caption_el:
            # Some pages might not have <caption>, skip
            continue
        caption_text = caption_el.get_text(strip=True)
        # Expected format: "<Team Name> Player Stats"
        team_name = caption_text.replace('Player Stats', '').strip()
        # Try to infer a match id from URL path
        match_id_match = re.search(r'/matches/([a-f0-9]{8})', match_url)
        match_id = match_id_match.group(1) if match_id_match else ''

        rows = extract_player_rows_from_table(tbl, team_name, match_id, match_url)
        # Override started flag using lineup starters if available
        if starters_from_lineup:
            for r in rows:
                r.started = r.playerName in starters_from_lineup
        for r in rows:
            played_players.add(r.playerName)
        results.extend(rows)

    # Include unused subs from lineup sections
    match_id_match = re.search(r'/matches/([a-f0-9]{8})', match_url)
    match_id = match_id_match.group(1) if match_id_match else ''
    results.extend(extract_unused_subs_from_lineups(soup, played_players, match_id, match_url))

    return results


def load_already_processed_urls() -> set:
    if not os.path.exists(OUTPUT_JSONL):
        return set()
    processed = set()
    try:
        with open(OUTPUT_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    processed.add(obj.get('matchUrl'))
                except Exception:
                    continue
    except Exception:
        return set()
    return processed


def append_jsonl(rows: List[AppearanceRow]) -> None:
    if not rows:
        return
    with open(OUTPUT_JSONL, 'a', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(asdict(row), ensure_ascii=False) + '\n')


def rebuild_full_json_from_jsonl() -> None:
    if not os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return
    all_rows: List[Dict] = []
    with open(OUTPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                all_rows.append(json.loads(line))
            except Exception:
                continue
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_rows, f, indent=2, ensure_ascii=False)


def save_failure(url: str, reason: str) -> None:
    with open(FAIL_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'url': url, 'reason': reason, 'ts': time.time()}) + '\n')


def main() -> None:
    fixtures = load_fixtures()

    # Build list of match URLs
    urls: List[str] = []
    for fixture in fixtures:
        url = fixture.get('match_report_url') or fixture.get('matchReportUrl') or fixture.get('match_report') or fixture.get('matchReport')
        if not url:
            continue
        urls.append(to_abs_url(url))

    urls = [u for u in urls if u]
    print(f'Total fixtures with match report URLs: {len(urls)}')

    processed = load_already_processed_urls()
    consecutive_fails = 0

    batch_counter = 0
    total_saved_rows = 0

    for idx, url in enumerate(urls, start=1):
        if url in processed:
            print(f'[{idx}/{len(urls)}] Skipping already processed: {url}')
            continue

        print(f'[{idx}/{len(urls)}] Fetching {url}')
        html = request_html(url)
        if not html:
            print(f'  Failed to fetch {url}')
            save_failure(url, 'fetch_failed')
            consecutive_fails += 1
            if consecutive_fails >= CONSECUTIVE_FAIL_CUTOFF:
                print('Too many consecutive failures; stopping for safety.')
                break
            time.sleep(random.uniform(*RANDOM_DELAY_RANGE_SECONDS))
            continue

        try:
            rows = extract_from_html(html, url)
        except Exception as e:
            print(f'  Parse error for {url}: {e}')
            save_failure(url, f'parse_error: {e}')
            consecutive_fails += 1
            if consecutive_fails >= CONSECUTIVE_FAIL_CUTOFF:
                print('Too many consecutive failures during parse; stopping for safety.')
                break
            time.sleep(random.uniform(*RANDOM_DELAY_RANGE_SECONDS))
            continue

        if not rows:
            print(f'  No rows extracted for {url}')
            save_failure(url, 'no_rows')
            consecutive_fails += 1
        else:
            append_jsonl(rows)
            total_saved_rows += len(rows)
            consecutive_fails = 0
            processed.add(url)
            print(f'  Saved {len(rows)} rows (total saved so far: {total_saved_rows})')

        # Random delay between requests
        time.sleep(random.uniform(*RANDOM_DELAY_RANGE_SECONDS))

        # Batch cooldown
        batch_counter += 1
        if batch_counter % BATCH_SIZE == 0:
            print(f'Completed batch of {BATCH_SIZE}. Cooling down for {BATCH_COOLDOWN_SECONDS}s...')
            time.sleep(BATCH_COOLDOWN_SECONDS)

    # Rebuild consolidated JSON at the end
    rebuild_full_json_from_jsonl()
    print(f'Done. Wrote JSONL to {OUTPUT_JSONL} and JSON to {OUTPUT_JSON}')


if __name__ == '__main__':
    main()
