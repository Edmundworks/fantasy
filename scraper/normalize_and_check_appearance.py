import json
import os
from typing import Dict, List, Set
from urllib.parse import urljoin

BASE_URL = 'https://fbref.com'
FIXTURES_PATH = os.path.join(os.path.dirname(__file__), 'fixtures_matches_debug.json')
APPEAR_JSON = os.path.join(os.path.dirname(__file__), 'appearance_data.json')
APPEAR_JSON_NORMALIZED = os.path.join(os.path.dirname(__file__), 'appearance_data_normalized.json')
MISSING_URLS_JSON = os.path.join(os.path.dirname(__file__), 'missing_appearance_urls.json')
INCOMPLETE_MATCHES_JSON = os.path.join(os.path.dirname(__file__), 'incomplete_matches.json')

TEAM_ALIASES: Dict[str, str] = {
    'Manchester Utd': 'Manchester United',
    'Man Utd': 'Manchester United',
    'West Ham Utd': 'West Ham',
    'Brighton & Hove Albion': 'Brighton and Hove Albion',
    'Wolves': 'Wolverhampton Wanderers',
    'Newcastle Utd': 'Newcastle United',
}


def to_abs_url(url: str) -> str:
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('/'):
        return urljoin(BASE_URL, url)
    return urljoin(BASE_URL + '/', url)


def normalize_team(name: str) -> str:
    if not name:
        return name
    n = name.replace('Table', '').strip()
    # Collapse double spaces
    while '  ' in n:
        n = n.replace('  ', ' ')
    # Apply aliases exact
    if n in TEAM_ALIASES:
        return TEAM_ALIASES[n]
    # Replace suffix/word Utd -> United when standalone word
    n = n.replace(' Utd', ' United')
    return n


def main() -> None:
    # Load fixtures
    with open(FIXTURES_PATH, 'r', encoding='utf-8') as f:
        fixtures = json.load(f)

    fixture_urls: Set[str] = set()
    if isinstance(fixtures, dict):
        for _, v in fixtures.items():
            u = v.get('match_report_url') or v.get('matchReportUrl')
            if u:
                fixture_urls.add(to_abs_url(u))
    else:
        for v in fixtures:
            u = v.get('match_report_url') or v.get('matchReportUrl')
            if u:
                fixture_urls.add(to_abs_url(u))

    # Load appearance data
    with open(APPEAR_JSON, 'r', encoding='utf-8') as f:
        rows: List[Dict] = json.load(f)

    # Normalize team names and build index
    per_match_teams: Dict[str, Set[str]] = {}
    for r in rows:
        r['teamName'] = normalize_team(r.get('teamName', ''))
        mu = r.get('matchUrl')
        if mu:
            per_match_teams.setdefault(mu, set()).add(r['teamName'])

    # Save normalized appearance data
    with open(APPEAR_JSON_NORMALIZED, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    # Find missing and incomplete
    present_urls = set(per_match_teams.keys())
    missing_urls = sorted(u for u in fixture_urls if u not in present_urls)
    extra_urls = sorted(u for u in present_urls if u not in fixture_urls)

    incomplete = []
    for url, teams in per_match_teams.items():
        if len(teams) != 2:
            incomplete.append({'url': url, 'teamsFound': sorted(list(teams))})

    with open(MISSING_URLS_JSON, 'w', encoding='utf-8') as f:
        json.dump(missing_urls, f, indent=2)

    with open(INCOMPLETE_MATCHES_JSON, 'w', encoding='utf-8') as f:
        json.dump(incomplete, f, indent=2)

    print(f'Total fixtures: {len(fixture_urls)}')
    print(f'Present in appearance: {len(present_urls)}')
    print(f'Missing: {len(missing_urls)} -> saved to {MISSING_URLS_JSON}')
    print(f'Extra: {len(extra_urls)}')
    print(f'Incomplete matches (!=2 teams): {len(incomplete)} -> saved to {INCOMPLETE_MATCHES_JSON}')


if __name__ == '__main__':
    main()