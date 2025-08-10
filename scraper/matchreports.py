import asyncio
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env.local (one directory up)
load_dotenv('../.env.local')

from browser_use import Agent
from browser_use.llm import ChatOpenAI

async def extract_match_reports():
    # Check if API key is loaded
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Make sure you have OPENAI_API_KEY in your .env.local file")
        return
    
    print("✅ OPENAI_API_KEY found")
    
    agent = Agent(
        task="""
        Go to https://fbref.com/en/comps/9/2024-2025/schedule/2024-2025-Premier-League-Scores-and-Fixtures
        
        IMPORTANT: Navigate like a human user to avoid rate limiting:
        - Wait 2-3 seconds between actions
        - Scroll naturally to view different parts of the page
        - Don't make rapid consecutive requests
        
        Find the fixtures table with columns: Wk, Day, Date, Time, Home, xG, Score, xG, Away, Attendance, Venue, Referee, Match Report, Notes
        
        Extract data from ALL 380 Premier League matches for the 2024-2025 season from this table:
        
        For each match row, extract:
        1. Gameweek number (column "Wk") 
        2. Home team name (column "Home")
        3. Away team name (column "Away") 
        4. Match report URL (from the "Match Report" column - extract the href link)
        
        IMPORTANT EXTRACTION RULES:
        - Extract ALL 380 matches, not just the visible ones
        - If the table is paginated or has "Show more" functionality, make sure to load all matches
        - For the Match Report URL, extract the full href attribute from the link
        - If a match doesn't have a match report yet (future matches), mark the URL as null
        - Take breaks between scrolling/clicking to avoid rate limiting
        
        Return the data as a JSON array where each match is an object with:
        {
            "gameweek": number,
            "home_team": "string",
            "away_team": "string", 
            "match_report_url": "string or null"
        }
        
        Make sure to include ALL 380 matches from the entire season.
        """,
        llm=ChatOpenAI(model="gpt-4o"),
    )
    
    print("🤖 Starting browser automation to extract match reports...")
    print("📊 This will extract all 380 Premier League matches for 2024-2025 season")
    
    result = await agent.run()
    
    print("\n" + "="*60)
    print("📊 EXTRACTED MATCH REPORTS DATA:")
    print("="*60)
    
    # Handle the browser_use API result structure
    try:
        # Try to get the final result
        if hasattr(result, 'all_results') and result.all_results:
            final_result = result.all_results[-1]
        elif hasattr(result, 'results') and result.results:
            final_result = result.results[-1]
        else:
            # Just print the result directly
            print("Result:", result)
            return
            
        if hasattr(final_result, 'extracted_content') and final_result.extracted_content:
            print("✅ Data extraction completed!")
            print(f"📝 Extracted content preview:")
            
            # Try to parse as JSON to validate structure
            try:
                matches_data = json.loads(final_result.extracted_content)
                print(f"📊 Total matches found: {len(matches_data)}")
                print(f"🔍 Sample match: {matches_data[0] if matches_data else 'No matches found'}")
            except json.JSONDecodeError:
                print("⚠️  Data is not in JSON format, saving as raw text")
            
            # Save to file
            with open('premier_league_matches_2024_2025.json', 'w') as f:
                f.write(final_result.extracted_content)
            print("\n💾 Data saved to premier_league_matches_2024_2025.json")
            
        else:
            print("❌ No extracted content found")
            
    except Exception as e:
        print(f"❌ Error processing result: {e}")
        print("Raw result:", result)
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(extract_match_reports())
