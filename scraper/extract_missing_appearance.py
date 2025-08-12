import json
import os
from typing import List

from extract_appearance_data import (
    request_html,
    extract_from_html,
    append_jsonl,
    rebuild_full_json_from_jsonl,
)

BASE_DIR = os.path.dirname(__file__)
MISSING_URLS_JSON = os.path.join(BASE_DIR, 'missing_appearance_urls.json')


def main() -> None:
    if not os.path.exists(MISSING_URLS_JSON):
        print('No missing_appearance_urls.json found.')
        return

    with open(MISSING_URLS_JSON, 'r', encoding='utf-8') as f:
        urls: List[str] = json.load(f)

    if not urls:
        print('No missing URLs to process.')
        return

    print(f'Processing {len(urls)} missing URLs...')

    total_rows = 0
    for url in urls:
        print(f'Fetching {url}')
        html = request_html(url)
        if not html:
            print(f'  Failed to fetch: {url}')
            continue
        try:
            rows = extract_from_html(html, url)
        except Exception as e:
            print(f'  Parse error for {url}: {e}')
            continue
        if not rows:
            print(f'  No rows extracted for {url}')
            continue
        append_jsonl(rows)
        total_rows += len(rows)
        print(f'  Saved {len(rows)} rows')

    rebuild_full_json_from_jsonl()
    print(f'Done. Added {total_rows} rows. Rebuilt consolidated JSON.')


if __name__ == '__main__':
    main()