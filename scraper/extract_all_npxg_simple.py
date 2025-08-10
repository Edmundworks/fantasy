#!/usr/bin/env python3
"""
Extract non-penalty expected goals (npxG) for all matches from fixtures JSON
with anti-bot detection measures and progressive saving
"""
import asyncio
import os
import json
import time
import random
import shutil
from dotenv import load_dotenv
from typing import Dict, List, Optional
from pydantic import BaseModel

# Load environment variables from .env.local (one directory up)
load_dotenv('../.env.local')

from browser_use import Agent
from browser_use.llm import ChatOpenAI
try:
    from browser_use.controller import Controller  # structured output
except Exception:  # pragma: no cover
    Controller = None


class MatchNPXG(BaseModel):
    home_team_npxg: str
    away_team_npxg: str
    home_team_name: str
    away_team_name: str

class NPXGExtractor:
    def __init__(self):
        self.results_file = 'all_matches_npxg.json'
        self.progress_file = 'npxg_progress.json'
        self.failures_file = 'npxg_failures.json'
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.max_failure_streak = 3  # auto-stop after this many consecutive failures
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    def load_existing_results(self) -> Dict:
        """Load existing results to resume from where we left off"""
        if os.path.exists(self.results_file):
            try:
                with open(self.results_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def load_progress(self) -> Dict:
        """Load progress tracking"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except:
                return {"processed_count": 0, "last_processed_url": None}
        return {"processed_count": 0, "last_processed_url": None}
    
    def save_results(self, results: Dict):
        """Save results to JSON file"""
        with open(self.results_file, 'w') as f:
            json.dump(results, f, indent=2)
    
    def save_progress(self, progress: Dict):
        """Save progress tracking"""
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

    def load_failures(self) -> List[Dict]:
        if os.path.exists(self.failures_file):
            try:
                with open(self.failures_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_failures(self, failures: List[Dict]):
        with open(self.failures_file, 'w') as f:
            json.dump(failures, f, indent=2)
    
    def clear_browser_cache(self):
        """Clear browser-use cache to avoid bot detection"""
        cache_path = os.path.expanduser("~/.config/browseruse/profiles/default")
        if os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path)
                print("🧹 Cleared browser-use cache")
            except Exception as e:
                print(f"⚠️  Could not clear cache: {e}")
    
    def get_matches_from_fixtures(self) -> List[Dict]:
        """Get all matches with URLs from fixtures JSON"""
        print("📝 Loading matches from fixtures_matches_debug.json...")
        
        with open('fixtures_matches_debug.json', 'r') as f:
            fixtures = json.load(f)
        
        match_list = []
        for i, fixture in enumerate(fixtures):
            if fixture.get('match_report_url'):
                url = fixture['match_report_url']
                if url.startswith('/'):
                    url = f"https://fbref.com{url}"
                
                match_list.append({
                    'id': f"fixture_{i}",
                    'home_team': fixture['home_team'],
                    'away_team': fixture['away_team'],
                    'url': url,
                    'gameweek': fixture.get('gameweek')
                })
        
        return match_list

    def compute_resume_index(self, matches: List[Dict], existing_results: Dict) -> int:
        """Determine the next match index to process based on existing all_matches_npxg.json.

        Strategy:
        - If result keys look like fixture_{i}, resume at max(i)+1
        - Otherwise, linear scan from start until we hit the first match id not present in results
        """
        if not existing_results:
            return 0

        # Fast path for fixture_{i}
        max_idx = -1
        for key in existing_results.keys():
            if isinstance(key, str) and key.startswith("fixture_"):
                try:
                    idx = int(key.split("_")[-1])
                    if idx > max_idx:
                        max_idx = idx
                except ValueError:
                    continue
        if max_idx >= 0:
            return max_idx + 1

        # Fallback: find first index whose match id is not in results
        done_ids = set(existing_results.keys())
        for i, m in enumerate(matches):
            if m.get('id') not in done_ids:
                return i
        return len(matches)
    
    async def extract_single_match(self, match_url: str) -> Optional[Dict]:
        """Extract npxG for a single match with enhanced anti-detection"""
        
        # Random delay before starting (4-12 seconds)
        delay = random.uniform(4, 12)
        print(f"⏱️  Waiting {delay:.1f}s before extraction...")
        await asyncio.sleep(delay)
        
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
1. Go to the match report page and wait for it to fully load
2. Scroll down VERY SLOWLY to find the first team's "Player Stats" table (this will be the home team)
   - Look for a table with header like "Arsenal Player Stats" or "Fulham Player Stats" etc.
   - This table will have columns including Player, Nation, Position, Age, Min, and under "Expected" section there will be "npxG"
3. In this table, scroll to the bottom row (footer) which shows totals like "16 Players" or "15 Players"
   - Find the npxG column (under the "Expected" header group)
   - CAREFULLY read the exact number in the npxG footer cell - it may be values like 2.3, 1.5, 0.8, etc.
   - Extract this EXACT total value - this is the home team's non-penalty expected goals
4. Continue scrolling down SLOWLY to find the second team's "Player Stats" table (this will be the away team)
   - Look for another similar table with a different team name like "Newcastle United Player Stats"
5. In the away team's table, find the same footer row totals
   - CAREFULLY read the exact number in the npxG footer cell for the away team
   - Extract the EXACT npxG value for the away team
 6. Navigate like a human user - scroll VERY slowly, pause 4-8 seconds between actions to avoid rate limiting
7. Return ONLY a JSON object with this exact format:
   {{
     "home_team_npxg": "1.2",
     "away_team_npxg": "0.8",
     "home_team_name": "Fulham",
     "away_team_name": "Newcastle United"
   }}

IMPORTANT:
- The npxG values are in the footer/totals row of each team's summary stats table
- Look for the "npxG" column which is under the "Expected" header group
- READ THE NUMBERS VERY CAREFULLY - distinguish between similar values like 2.0 vs 2.3
- Double-check each number before extracting - precision is critical
 - Scroll VERY slowly and pause 4-8 seconds between actions to behave like a human
- Extract the exact numbers as strings with proper decimal precision
 - Only return the JSON object, nothing else""",
            llm=ChatOpenAI(model="gpt-4.1"),
        )
        if controller is not None:
            agent_kwargs["controller"] = controller
        agent = Agent(**agent_kwargs)
        
        try:
            print("🤖 Starting browser automation...")
            result = await agent.run()
            
            # Extract the final result using robust parsing
            content = None
            # Prefer controller final_result when available
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
                    if not content and result.all_results:
                        content = getattr(result.all_results[-1], 'extracted_content', None)
                        if callable(content):
                            content = content()
                        if content is not None and not isinstance(content, str):
                            try:
                                content = str(content)
                            except Exception:
                                content = None
                except Exception:
                    content = None

            if not content:
                # Try direct content/text
                content = (
                    getattr(result, 'content', None)
                    or getattr(result, 'text', None)
                    or getattr(result, 'extracted_content', None)
                )
                if callable(content):
                    content = content()
                if content is not None and not isinstance(content, str):
                    try:
                        content = str(content)
                    except Exception:
                        content = None

            raw_result_str = None
            if not content:
                try:
                    raw_result_str = str(result)
                except Exception:
                    raw_result_str = None

            if not content:
                if raw_result_str:
                    import re
                    json_match = re.search(r'\{\s*"home_team_npxg"[^}]*\}', raw_result_str)
                    if json_match:
                        content = json_match.group(0)
                        if content is not None and not isinstance(content, str):
                            try:
                                content = str(content)
                            except Exception:
                                content = None
            
            if not content:
                print("❌ No content found in result")
                return None
            
            # Parse JSON from content
            try:
                data = json.loads(content)
                print("✅ Successfully parsed JSON directly!")
            except json.JSONDecodeError:
                import re
                patt1 = r'\{"home_team_npxg":\s*"[^"]*",\s*"away_team_npxg":\s*"[^"]*",\s*"home_team_name":\s*"[^"]*",\s*"away_team_name":\s*"[^"]*"\}'
                patt2 = r'\{\s*\"home_team_npxg\"[^}]*\}'
                m = re.search(patt1, content) or re.search(patt2, content)
                if m:
                    data = json.loads(m.group())
                else:
                    return None
            
            print(f"🏠 Home team ({data.get('home_team_name', 'Unknown')}): {data.get('home_team_npxg', 'N/A')}")
            print(f"✈️  Away team ({data.get('away_team_name', 'Unknown')}): {data.get('away_team_npxg', 'N/A')}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            return None
    
    async def process_all_matches(self):
        """Process all matches with anti-bot measures"""
        print("🚀 Starting bulk npxG extraction for all matches...")
        
        # Load existing data
        results = self.load_existing_results()
        progress = self.load_progress()
        
        # Get all matches
        matches = self.get_matches_from_fixtures()
        total_matches = len(matches)
        
        # Compute resume point from all_matches_npxg.json (authoritative)
        resume_index = self.compute_resume_index(matches, results)
        progress['processed_count'] = resume_index
        self.save_progress(progress)

        print(f"📊 Found {total_matches} matches to process")
        print(f"📋 Resuming from match #{resume_index}")
        
        failures = self.load_failures()
        failure_streak = 0
        long_rest_every = random.randint(12, 20)

        for i, match in enumerate(matches):
            if i < resume_index:
                continue  # Skip already processed matches
            
            match_id = match['id']
            match_url = match['url']
            
            print(f"\n{'='*80}")
            print(f"📝 Processing match {i+1}/{total_matches}")
            print(f"🆚 {match['home_team']} vs {match['away_team']}")
            print(f"🔗 {match_url}")
            print(f"{'='*80}")
            
            # Skip if already have result for this match
            if match_id in results:
                print("✅ Already processed, skipping...")
                continue
            
            # Clear browser cache every 4-7 matches (random) to avoid detection
            if i > 0 and (i % random.randint(4, 7) == 0):
                print("🧹 Clearing browser cache (anti-detection measure)...")
                self.clear_browser_cache()
                print("⏱️  Extended pause for anti-detection...")
                await asyncio.sleep(random.uniform(12, 25))
            
            # Extract npxG for this match
            match_data = await self.extract_single_match(match_url)
            
            if match_data:
                # Add metadata
                match_data['match_id'] = match_id
                match_data['match_url'] = match_url
                match_data['gameweek'] = match.get('gameweek')
                match_data['processed_at'] = time.time()
                
                # Store result
                results[match_id] = match_data
                
                # Update progress
                progress['processed_count'] = i + 1
                resume_index = progress['processed_count']
                progress['last_processed_url'] = match_url
                progress['last_processed_at'] = time.time()
                
                # Save immediately after each successful extraction
                self.save_results(results)
                self.save_progress(progress)
                
                print(f"✅ Saved result for match {i+1}/{total_matches}")
                failure_streak = 0  # reset streak on success
            else:
                print(f"❌ Failed to extract data for match {i+1}/{total_matches}")
                failures.append({
                    'match_id': match_id,
                    'url': match_url,
                    'home_team': match.get('home_team'),
                    'away_team': match.get('away_team'),
                    'failed_at': time.time()
                })
                self.save_failures(failures)
                failure_streak += 1
                if failure_streak >= self.max_failure_streak:
                    print(f"🛑 Stopping early after {failure_streak} consecutive failures (safety cutoff)")
                    break
            
            # Anti-detection pause between matches (7-18 seconds) + occasional long rest
            if i < total_matches - 1:  # Don't pause after the last match
                if (i + 1) % long_rest_every == 0:
                    pause_time = random.uniform(35, 60)
                    print(f"⏱️  Long rest: {pause_time:.1f}s (anti-detection)...")
                else:
                    pause_time = random.uniform(7, 18)
                print(f"⏱️  Anti-detection pause: {pause_time:.1f}s...")
                await asyncio.sleep(pause_time)
        
        print(f"\n🎉 Completed processing all {total_matches} matches!")
        print(f"📊 Successfully extracted: {len(results)} matches")
        print(f"💾 Results saved to: {self.results_file}")
        
        return results

async def main():
    """Main function to run the bulk extraction"""
    extractor = NPXGExtractor()
    
    try:
        results = await extractor.process_all_matches()
        print(f"\n✅ Extraction complete! Processed {len(results)} matches")
        
        # Print summary stats safely
        successful_extractions = sum(1 for r in results.values() if r.get('home_team_npxg') is not None)
        total_done = max(1, len(results))
        print(f"📈 Success rate: {successful_extractions}/{len(results)} ({100*successful_extractions/total_done:.1f}%)")
        
    except KeyboardInterrupt:
        print("\n⏹️  Extraction stopped by user. Progress has been saved.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())