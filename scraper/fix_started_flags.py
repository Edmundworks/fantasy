import json
import os
import random
import time
from typing import Dict, List, Set

from bs4 import BeautifulSoup
from extract_appearance_data import request_html

BASE_DIR = os.path.dirname(__file__)
APPEAR_JSON = os.path.join(BASE_DIR, 'appearance_data.json')
APPEAR_JSON_FIXED = os.path.join(BASE_DIR, 'appearance_data_fixed.json')

RANDOM_DELAY_RANGE_SECONDS = (0.5, 1.5)


def get_lineup_starters_from_html(html: str) -> Set[str]:
    starters: Set[str] = set()
    soup = BeautifulSoup(html, 'html.parser')
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
            tds = tr.find_all('td')
            if len(tds) < 2:
                continue
            a = tds[1].find('a')
            name = a.get_text(strip=True) if a else tds[1].get_text(strip=True)
            if name:
                starters.add(name)
    return starters


def main() -> None:
    with open(APPEAR_JSON, 'r', encoding='utf-8') as f:
        data: List[Dict] = json.load(f)

    # Group rows by matchUrl
    by_url: Dict[str, List[Dict]] = {}
    for r in data:
        mu = r.get('matchUrl')
        if not mu:
            continue
        by_url.setdefault(mu, []).append(r)

    print(f'Total matches to process: {len(by_url)}')

    fixed_count = 0
    for i, (url, rows) in enumerate(by_url.items(), start=1):
        print(f'[{i}/{len(by_url)}] Fetching lineup for {url}')
        html = request_html(url)
        if not html:
            print('  fetch failed, skipping')
            continue
        starters = get_lineup_starters_from_html(html)
        if not starters:
            print('  no starters parsed, skipping')
            continue
        # Update started flags
        for r in rows:
            r['started'] = r.get('playerName') in starters
            fixed_count += 1
        time.sleep(random.uniform(*RANDOM_DELAY_RANGE_SECONDS))

    with open(APPEAR_JSON_FIXED, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f'Done. Updated started flags for {fixed_count} rows.')
    print(f'Wrote fixed file to {APPEAR_JSON_FIXED}')


if __name__ == '__main__':
    main()