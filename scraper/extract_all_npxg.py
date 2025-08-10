#!/usr/bin/env python3
"""
Extract non-penalty expected goals (npxG) for all matches from the database
with anti-bot detection measures and progressive saving
"""
import asyncio
import os
import json
import time
import random
import subprocess
import shutil
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Load environment variables from .env.local (one directory up)
load_dotenv('../.env.local')

from browser_use import Agent
from browser_use.llm import ChatOpenAI

class NPXGExtractor:
    def __init__(self):
        self.results_file = 'all_matches_npxg.json'
        self.progress_file = 'npxg_progress.json'
        self.api_key = os.getenv('OPENAI_API_KEY')
        
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
    
    def clear_browser_cache(self):
        """Clear browser-use cache to avoid bot detection"""
        cache_path = os.path.expanduser("~/.config/browseruse/profiles/default")
        if os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path)
                print("🧹 Cleared browser-use cache")
            except Exception as e:
                print(f"⚠️  Could not clear cache: {e}")
    
    def get_matches_from_db(self) -> List[Dict]:
        """Get all matches with URLs from the database"""
        # Import here to avoid issues with path resolution
        import sys
        sys.path.append('../src')
        
        try:
            from db.index import db
            from db.schema import matches
            from drizzle_orm import isNotNull
            
            # Get all matches that have match report URLs
            query = db.select().from(matches).where(isNotNull(matches.matchReportUrl))
            query_results = query.execute()
            
            match_list = []
            for match in query_results:
                # Convert relative URLs to full URLs
                url = match.matchReportUrl
                if url and url.startswith('/'):
                    url = f"https://fbref.com{url}"
                
                match_list.append({
                    'id': match.id,
                    'home_team': match.homeTeamName,
                    'away_team': match.awayTeamName,
                    'url': url,
                    'gameweek': match.gameweek
                })
            
            return match_list
        
        except Exception as e:
            print(f"❌ Error getting matches from database: {e}")
            print("📝 Using fixture debug JSON as fallback...")
            
            # Fallback: use the fixture debug JSON
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
    
    async def extract_single_match(self, match_url: str) -> Optional[Dict]:
        """Extract npxG for a single match with enhanced anti-detection"""
        
        # Random delay before starting (2-8 seconds)
        delay = random.uniform(2, 8)
        print(f"⏱️  Waiting {delay:.1f}s before extraction...")
        await asyncio.sleep(delay)
        
        agent = Agent(
            task=f"""Navigate to the FBref match report page and extract non-penalty expected goals (npxG) for both teams.

URL to visit: {match_url}

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
6. Navigate like a human user - scroll VERY slowly, pause 4-6 seconds between actions to avoid rate limiting
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
- Scroll VERY slowly and pause 4-6 seconds between actions to behave like a human
- Extract the exact numbers as strings with proper decimal precision
- Only return the JSON object, nothing else""",
            llm=ChatOpenAI(model="gpt-4.1"),
        )
        
        try:
            print("🤖 Starting browser automation...")
            result = await agent.run()
            
            # Extract the final result using our proven parsing logic
            content = None
            if hasattr(result, 'all_results'):
                for action_result in result.all_results:
                    if hasattr(action_result, 'is_done') and action_result.is_done:
                        content = action_result.extracted_content
                        break
                else:
                    content = result.all_results[-1].extracted_content if result.all_results else None
            
            if not content:
                print("❌ No content found in result")
                return None
            
            # Parse JSON from content
            try:
                data = json.loads(content)
                print("✅ Successfully parsed JSON directly!")
            except json.JSONDecodeError:
                import re
                json_pattern = r'\{"home_team_npxg":\s*"[^"]*",\s*"away_team_npxg":\s*"[^"]*",\s*"home_team_name":\s*"[^"]*",\s*"away_team_name":\s*"[^"]*"\}'
                json_match = re.search(json_pattern, content)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)
                    print("✅ Successfully extracted JSON from content!")
                else:
                    print("❌ Could not parse JSON")
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
        matches = self.get_matches_from_db()
        total_matches = len(matches)
        
        print(f"📊 Found {total_matches} matches to process")
        print(f"📋 Resuming from match #{progress['processed_count']}")
        
        for i, match in enumerate(matches):
            if i < progress['processed_count']:
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
            
            # Clear browser cache every 5 matches to avoid detection
            if i % 5 == 0 and i > 0:
                print("🧹 Clearing browser cache (anti-detection measure)...")
                self.clear_browser_cache()
                print("⏱️  Extended pause for anti-detection...")
                await asyncio.sleep(random.uniform(10, 20))
            
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
                progress['last_processed_url'] = match_url
                progress['last_processed_at'] = time.time()
                
                # Save immediately after each successful extraction
                self.save_results(results)
                self.save_progress(progress)
                
                print(f"✅ Saved result for match {i+1}/{total_matches}")
            else:
                print(f"❌ Failed to extract data for match {i+1}/{total_matches}")
            
            # Anti-detection pause between matches (5-15 seconds)
            if i < total_matches - 1:  # Don't pause after the last match
                pause_time = random.uniform(5, 15)
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
        
        # Print summary stats
        successful_extractions = sum(1 for r in results.values() if r.get('home_team_npxg') is not None)
        print(f"📈 Success rate: {successful_extractions}/{len(results)} ({100*successful_extractions/len(results):.1f}%)")
        
    except KeyboardInterrupt:
        print("\n⏹️  Extraction stopped by user. Progress has been saved.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())