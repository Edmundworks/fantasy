#!/usr/bin/env python3
"""
Extract missing npxG entries for a fixed set of FBref match report URLs.
- Hardcoded list of missing URLs
- Maps to original fixture ids via fixtures_matches_debug.json
- Requests-based primary extraction, browser-use fallback
- Appends/merges into all_matches_npxg.json, saving after each success
"""
import asyncio
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup, Comment
from dotenv import load_dotenv
from pydantic import BaseModel

# Load env one directory up
load_dotenv('../.env.local')

# Optional browser-use fallback
try:
    from browser_use import Agent
    from browser_use.llm import ChatOpenAI
    try:
        from browser_use.controller import Controller  # structured output
    except Exception:
        Controller = None
except Exception:  # pragma: no cover
    Agent = None
    ChatOpenAI = None
    Controller = None

ROOT = Path(__file__).parent
FIXTURES_PATH = ROOT / 'fixtures_matches_debug.json'
RESULTS_PATH = ROOT / 'all_matches_npxg.json'
PROGRESS_PATH = ROOT / 'npxg_progress_missing.json'

MISSING_URLS: List[str] = [
    "https://fbref.com/en/matches/4d0079fb/Fulham-Leicester-City-August-24-2024-Premier-League",
    "https://fbref.com/en/matches/54405f8a/Manchester-City-Brentford-September-14-2024-Premier-League",
    "https://fbref.com/en/matches/929e225f/Crystal-Palace-Manchester-United-September-21-2024-Premier-League",
    "https://fbref.com/en/matches/a24b7a43/Manchester-City-Ipswich-Town-August-24-2024-Premier-League",
    "https://fbref.com/en/matches/b4df0bca/Newcastle-United-Manchester-City-September-28-2024-Premier-League",
    "https://fbref.com/en/matches/b96c3759/Southampton-Manchester-United-September-14-2024-Premier-League",
    "https://fbref.com/en/matches/d701a1df/Brighton-and-Hove-Albion-Nottingham-Forest-September-22-2024-Premier-League",
    "https://fbref.com/en/matches/d7538020/Manchester-City-Arsenal-September-22-2024-Premier-League",
    "https://fbref.com/en/matches/e76c15c9/Wolverhampton-Wanderers-Chelsea-August-25-2024-Premier-League",
]

class MatchNPXG(BaseModel):
    home_team_npxg: str
    away_team_npxg: str
    home_team_name: str
    away_team_name: str

class MissingNPXGExtractor:
    def __init__(self) -> None:
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://fbref.com/',
        }
        # gentle delays
        self.min_delay_sec = 5
        self.max_delay_sec = 12

    # ---------- IO ----------
    def load_results(self) -> Dict:
        if RESULTS_PATH.exists():
            try:
                return json.loads(RESULTS_PATH.read_text())
            except Exception:
                return {}
        return {}

    def save_results(self, results: Dict) -> None:
        RESULTS_PATH.write_text(json.dumps(results, indent=2))

    def load_progress(self) -> Dict:
        if PROGRESS_PATH.exists():
            try:
                return json.loads(PROGRESS_PATH.read_text())
            except Exception:
                return {"done": []}
        return {"done": []}

    def save_progress(self, progress: Dict) -> None:
        PROGRESS_PATH.write_text(json.dumps(progress, indent=2))

    def build_fixture_lookup(self) -> Dict[str, Dict]:
        fixtures = json.loads(FIXTURES_PATH.read_text())
        lookup: Dict[str, Dict] = {}
        for idx, fx in enumerate(fixtures):
            u = fx.get('match_report_url') or ''
            if not u:
                continue
            if u.startswith('/'):
                u = f"https://fbref.com{u}"
            lookup[u] = {
                'id': f"fixture_{idx}",
                'home_team': fx.get('home_team'),
                'away_team': fx.get('away_team'),
                'gameweek': fx.get('gameweek'),
                'url': u,
            }
        return lookup

    # ---------- HTML Parsing ----------
    def _extract_teams_from_title(self, soup: BeautifulSoup) -> Optional[List[str]]:
        h1 = soup.find('h1')
        if not h1:
            return None
        text = ' '.join(h1.get_text(strip=True).split())
        text = text.replace('—', '-').replace('–', '-')
        m = re.search(r'^(.*?)\s+vs\.\s+(.*?)\s+(Match Report|Preview|Head-to-Head)', text, flags=re.IGNORECASE)
        if m:
            return [m.group(1).strip(), m.group(2).strip()]
        return None

    def _parse_npxg_from_html(self, html: str) -> Optional[Dict[str, str]]:
        soup = BeautifulSoup(html, 'html.parser')
        # Expand commented tables
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            try:
                frag = BeautifulSoup(c, 'html.parser')
                c.replace_with(frag)
            except Exception:
                pass

        teams_from_title = self._extract_teams_from_title(soup) or [None, None]

        # Find the two summary tables
        tables: List[BeautifulSoup] = []
        for tbl in soup.find_all('table'):
            tid = tbl.get('id') or ''
            if re.match(r'^stats_.*_summary$', tid):
                tables.append(tbl)
        if len(tables) < 2:
            for tbl in soup.find_all('table'):
                cls = ' '.join(tbl.get('class', []))
                if 'summary' in cls:
                    tables.append(tbl)
            tables = tables[:2]
        if len(tables) < 2:
            return None

        def read_team_name_for_table(table: BeautifulSoup) -> Optional[str]:
            prev = table
            for _ in range(8):
                prev = prev.find_previous(['h2', 'h3'])
                if not prev:
                    break
                t = prev.get_text(strip=True)
                m = re.match(r'^(.*?)\s+Player Stats', t, flags=re.IGNORECASE)
                if m:
                    return m.group(1).strip()
            return None

        def read_npxg(table: BeautifulSoup) -> Optional[str]:
            tfoot = table.find('tfoot')
            if not tfoot:
                return None
            cell = tfoot.find('td', attrs={'data-stat': 'npxg'})
            if not cell:
                last_row = tfoot.find('tr')
                if not last_row:
                    return None
                cells = last_row.find_all(['td', 'th'])
                for c in cells:
                    if (c.get('data-stat') or '').lower() == 'npxg':
                        cell = c
                        break
            if not cell:
                return None
            val = cell.get_text(strip=True)
            return val if val else None

        first_tbl, second_tbl = tables[0], tables[1]
        home_name = read_team_name_for_table(first_tbl) or teams_from_title[0]
        away_name = read_team_name_for_table(second_tbl) or teams_from_title[1]
        home_npxg = read_npxg(first_tbl)
        away_npxg = read_npxg(second_tbl)

        if not (home_name and away_name and home_npxg is not None and away_npxg is not None):
            return None

        return {
            'home_team_npxg': home_npxg,
            'away_team_npxg': away_npxg,
            'home_team_name': home_name,
            'away_team_name': away_name,
        }

    def fetch_npxg_via_requests(self, match_url: str) -> Optional[Dict[str, str]]:
        for attempt in range(3):
            try:
                resp = requests.get(match_url, headers=self.headers, timeout=30)
                if resp.status_code == 200 and resp.text:
                    parsed = self._parse_npxg_from_html(resp.text)
                    if parsed:
                        return parsed
                time.sleep(1.5 * (attempt + 1))
            except Exception:
                time.sleep(1.5 * (attempt + 1))
        return None

    async def extract_single_match_via_browser(self, match_url: str) -> Optional[Dict[str, str]]:
        if Agent is None or ChatOpenAI is None:
            return None
        controller = None
        if Controller is not None:
            try:
                controller = Controller(output_model=MatchNPXG)
            except Exception:
                controller = None
        agent_kwargs = dict(
            task=f"""Behave like a careful human user and extract non-penalty expected goals (npxG) for both teams.

Step 0: First open https://fbref.com/ and wait 4-6 seconds.
Step 1: Then go to the specific match report URL: {match_url}

INSTRUCTIONS:
- Find each team's Player Stats summary table
- In the footer row, read the npxG total
- Return ONLY JSON:
{{
  "home_team_npxg": "1.2",
  "away_team_npxg": "0.8",
  "home_team_name": "Fulham",
  "away_team_name": "Newcastle United"
}}
""",
            llm=ChatOpenAI(model="gpt-4.1"),
        )
        if controller is not None:
            agent_kwargs["controller"] = controller
        agent = Agent(**agent_kwargs)
        try:
            result = await agent.run()
            # Try controller final result first
            content = None
            try:
                final_result_method = getattr(result, "final_result", None)
                if callable(final_result_method):
                    content = final_result_method()
                    if callable(content):
                        content = content()
                    if content is not None and not isinstance(content, str):
                        content = str(content)
            except Exception:
                content = content
            if hasattr(result, 'all_results'):
                try:
                    for action_result in result.all_results:
                        if getattr(action_result, 'is_done', False):
                            content = getattr(action_result, 'extracted_content', None)
                            if callable(content):
                                content = content()
                            if content is not None and not isinstance(content, str):
                                try:
                                    content = str(content)
                                except Exception:
                                    content = None
                            if content:
                                break
                except Exception:
                    content = content
            if not content:
                content = getattr(result, 'content', None) or getattr(result, 'text', None) or getattr(result, 'extracted_content', None)
                if callable(content):
                    content = content()
                if content is not None and not isinstance(content, str):
                    try:
                        content = str(content)
                    except Exception:
                        content = None
            if not content:
                try:
                    raw = str(result)
                except Exception:
                    raw = None
                if raw:
                    m = re.search(r'\{\s*"home_team_npxg"[^}]*\}', raw)
                    if m:
                        content = m.group(0)
            if not content:
                return None
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                m = re.search(r'\{\s*"home_team_npxg"[^}]*\}', content)
                if not m:
                    return None
                data = json.loads(m.group(0))
            return data
        except Exception:
            return None

    # ---------- Orchestration ----------
    async def process_missing(self) -> Dict:
        print("🚀 Processing only missing matches (hardcoded list)...")
        results = self.load_results()
        progress = self.load_progress()
        done_urls = set(progress.get('done', []))
        lookup = self.build_fixture_lookup()

        processed = 0
        for idx, url in enumerate(MISSING_URLS, start=1):
            print("\n" + "=" * 80)
            print(f"📝 Missing {idx}/{len(MISSING_URLS)}")
            print(f"🔗 {url}")
            print("=" * 80)

            # Skip if already done in this run
            if url in done_urls:
                print("✅ Already processed in this missing-run, skipping...")
                continue

            # Skip if already present in main results
            if any((v.get('match_url') == url) for v in results.values()):
                print("✅ Already present in all_matches_npxg.json, skipping...")
                progress['done'] = list(sorted(done_urls | {url}))
                self.save_progress(progress)
                continue

            # Fixture info (id/home/away)
            meta = lookup.get(url)
            if not meta:
                print("⚠️  Could not map URL to fixture id from fixtures_matches_debug.json; will assign a temporary id")
                temp_id = f"manual_{int(time.time())}_{idx}"
            else:
                temp_id = meta['id']
                print(f"🆔 Using fixture id: {temp_id}")
                print(f"🆚 {meta.get('home_team')} vs {meta.get('away_team')}")

            # Jitter delay
            delay = random.uniform(self.min_delay_sec, self.max_delay_sec)
            print(f"⏱️  Waiting {delay:.1f}s before extraction...")
            await asyncio.sleep(delay)

            # Primary path: requests
            data = self.fetch_npxg_via_requests(url)
            # Fallback: browser-use
            if not data:
                print("🤖 Falling back to browser-use agent...")
                data = await self.extract_single_match_via_browser(url)

            if not data:
                print("❌ Failed to extract. Will continue to next.")
                continue

            # Merge result
            data['match_id'] = temp_id
            data['match_url'] = url
            if meta:
                data['gameweek'] = meta.get('gameweek')
            data['processed_at'] = time.time()
            results[temp_id] = data

            # Save after each
            self.save_results(results)
            done_urls.add(url)
            progress['done'] = list(sorted(done_urls))
            self.save_progress(progress)

            processed += 1
            print(f"✅ Saved missing result ({processed}/{len(MISSING_URLS)})")
            if idx < len(MISSING_URLS):
                pause = random.uniform(7, 16)
                print(f"⏱️  Anti-detection pause: {pause:.1f}s...")
                await asyncio.sleep(pause)

        print("\n🎉 Finished processing hardcoded missing matches.")
        print(f"📊 Now in results: {len(results)} entries")
        return results

async def main() -> None:
    extractor = MissingNPXGExtractor()
    try:
        results = await extractor.process_missing()
        print(f"\n✅ Done. Results entries: {len(results)}")
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user; progress is saved.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == '__main__':
    asyncio.run(main())