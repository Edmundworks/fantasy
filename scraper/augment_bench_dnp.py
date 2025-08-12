import json
import os
from typing import Dict, List, Set, Tuple

from extract_appearance_data import (
    load_fixtures,
    to_abs_url,
    request_html,
    extract_from_html,
    append_jsonl,
    rebuild_full_json_from_jsonl,
)

BASE_DIR = os.path.dirname(__file__)
APPEAR_JSON = os.path.join(BASE_DIR, 'appearance_data.json')


def load_existing_index() -> Dict[str, Set[Tuple[str, str]]]:
    """Map matchUrl -> set of (playerName, teamName) already present."""
    if not os.path.exists(APPEAR_JSON):
        return {}
    with open(APPEAR_JSON, 'r', encoding='utf-8') as f:
        data: List[Dict] = json.load(f)
    idx: Dict[str, Set[Tuple[str, str]]] = {}
    for r in data:
        mu = r.get('matchUrl')
        pn = r.get('playerName')
        tn = r.get('teamName')
        if not mu or not pn or not tn:
            continue
        idx.setdefault(mu, set()).add((pn, tn))
    return idx


def main() -> None:
    fixtures = load_fixtures()
    urls: List[str] = []
    for fx in fixtures:
        u = fx.get('match_report_url') or fx.get('matchReportUrl')
        if u:
            urls.append(to_abs_url(u))

    existing = load_existing_index()

    added_rows = 0
    processed_urls = 0

    for i, url in enumerate(urls, start=1):
        print(f'[{i}/{len(urls)}] Processing {url}')
        html = request_html(url)
        if not html:
            print('  fetch failed, skipping')
            continue
        try:
            rows = extract_from_html(html, url)
        except Exception as e:
            print(f'  parse error: {e}')
            continue

        if not rows:
            print('  no rows extracted')
            continue

        # Only keep rows that are bench DNP (minutes_played is None)
        # and are not already present for this matchUrl
        existing_set = existing.get(url, set())
        new_rows = []
        for r in rows:
            if r.minutes_played is None:
                key = (r.playerName, r.teamName)
                if key not in existing_set:
                    new_rows.append(r)

        if new_rows:
            append_jsonl(new_rows)
            added_rows += len(new_rows)
            # update index to avoid duplicates later in run
            if url not in existing:
                existing[url] = set()
            for r in new_rows:
                existing[url].add((r.playerName, r.teamName))
            print(f'  added {len(new_rows)} bench DNP rows')
        else:
            print('  nothing to add')

        processed_urls += 1

    rebuild_full_json_from_jsonl()
    print(f'Done. Processed {processed_urls} URLs, added {added_rows} rows.')


if __name__ == '__main__':
    main()