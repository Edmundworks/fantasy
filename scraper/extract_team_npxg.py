#!/usr/bin/env python3
"""
Extract non-penalty expected goals (npxG) for both teams from FBref match reports
"""
import asyncio
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env.local (one directory up)
load_dotenv('../.env.local')

from browser_use import Agent
from browser_use.llm import ChatOpenAI

async def extract_team_npxg(match_url):
    """Extract npxG for both teams from a match report"""
    
    # Check if API key is loaded
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Make sure you have OPENAI_API_KEY in your .env.local file")
        return None
    
    print("✅ OPENAI_API_KEY found")
    print(f"🔍 Extracting team npxG from: {match_url}")
    
    agent = Agent(
        task=f"""Navigate to the FBref match report page and extract non-penalty expected goals (npxG) for both teams.

URL to visit: {match_url}

INSTRUCTIONS:
1. Go to the match report page
2. Scroll down slowly to find the first team's "Player Stats" table (this will be the home team)
   - Look for a table with header like "Arsenal Player Stats" or "Fulham Player Stats" etc.
   - This table will have columns including Player, Nation, Position, Age, Min, and under "Expected" section there will be "npxG"
3. In this table, scroll to the bottom row (footer) which shows totals like "16 Players" or "15 Players"
   - Find the npxG column (under the "Expected" header group)
   - CAREFULLY read the exact number in the npxG footer cell - it may be values like 2.3, 1.5, 0.8, etc.
   - Extract this EXACT total value - this is the home team's non-penalty expected goals
4. Continue scrolling down to find the second team's "Player Stats" table (this will be the away team)
   - Look for another similar table with a different team name like "Newcastle United Player Stats"
5. In the away team's table, find the same footer row totals
   - CAREFULLY read the exact number in the npxG footer cell for the away team
   - Extract the EXACT npxG value for the away team
6. Navigate like a human user - scroll slowly, pause between actions to avoid rate limiting
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
- Scroll slowly and pause between actions to behave like a human
- Extract the exact numbers as strings with proper decimal precision
- Only return the JSON object, nothing else""",
        llm=ChatOpenAI(model="gpt-4.1"),
    )
    
    try:
        print("🤖 Starting browser automation...")
        result = await agent.run()
        
        print("\n" + "="*60)
        print("📊 EXTRACTION RESULT")
        print("="*60)
        
        # Try to parse the result as JSON
        try:
            content = None
            
            # Handle AgentHistoryList from browser-use
            if hasattr(result, 'all_results'):
                # Find the final result with is_done=True
                for action_result in result.all_results:
                    if hasattr(action_result, 'is_done') and action_result.is_done:
                        content = action_result.extracted_content
                        break
                else:
                    # Fallback: use the last result
                    content = result.all_results[-1].extracted_content if result.all_results else None
            elif hasattr(result, 'content'):
                content = result.content
            elif hasattr(result, 'text'):
                content = result.text
            else:
                content = str(result)
            
            if not content:
                print("❌ No content found in result")
                return None
                
            print(f"🔍 Extracted content: {content[:200]}...")
            
            # Try to parse the content directly as JSON first
            try:
                data = json.loads(content)
                print("✅ Successfully parsed JSON directly!")
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the content
                import re
                # Look for the JSON pattern in the content
                json_pattern = r'\{"home_team_npxg":\s*"[^"]*",\s*"away_team_npxg":\s*"[^"]*",\s*"home_team_name":\s*"[^"]*",\s*"away_team_name":\s*"[^"]*"\}'
                json_match = re.search(json_pattern, content)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)
                    print("✅ Successfully extracted JSON from content!")
                else:
                    # Fallback: simple JSON extraction
                    simple_json_match = re.search(r'\{[^}]*"home_team_npxg"[^}]*\}', content)
                    if simple_json_match:
                        json_str = simple_json_match.group()
                        data = json.loads(json_str)
                        print("✅ Successfully extracted JSON with fallback method!")
                    else:
                        print("❌ Could not find valid JSON in result")
                        print(f"Raw content preview: {content[:500]}...")
                        return None
            
            print("✅ Successfully extracted team npxG data!")
            print(f"🏠 Home team ({data.get('home_team_name', 'Unknown')}): {data.get('home_team_npxg', 'N/A')}")
            print(f"✈️  Away team ({data.get('away_team_name', 'Unknown')}): {data.get('away_team_npxg', 'N/A')}")
            
            return data
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Raw content: {content}")
            return None
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return None

async def test_extraction():
    """Test the extraction with a sample match"""
    # Use the sample match we analyzed
    test_url = "https://fbref.com/en/matches/de7298df/Fulham-Newcastle-United-September-21-2024-Premier-League"
    
    print("🧪 Testing npxG extraction...")
    result = await extract_team_npxg(test_url)
    
    if result:
        print("\n✅ Test successful!")
        
        # Save result for inspection
        with open('test_npxg_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("💾 Result saved to test_npxg_result.json")
    else:
        print("\n❌ Test failed!")

if __name__ == "__main__":
    asyncio.run(test_extraction())