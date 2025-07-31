import asyncio
import os
import json
from dotenv import load_dotenv

#todo
# script that gets all the match report URLS
# then script that steps through each match report and gets the player stats
# and saves them to a database

# Load environment variables from .env.local (one directory up)
load_dotenv('../.env.local')

from browser_use import Agent
from browser_use.llm import ChatOpenAI

async def test_fbref():
    # Check if API key is loaded
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Make sure you have OPENAI_API_KEY in your .env.local file")
        return
    
    print("✅ OPENAI_API_KEY found")
    
    agent = Agent(
        task="""
        Go to https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures
        
        Click into the first match report
        
        Remember the two team names, home team is the first team and away team is the second team
        
        Look for a span with class="section_anchor" and data-label containing "Player Stats" in the format
        first team name Player Stats e.g. Arsenal Player Stats
        
        Navigate to that section to find the player statistics tables
        
        Look for tables with columns including "npxG" and "xAG"
        
        Extract ALL player names and their npxG and xAG values (do not truncate the list)
        
        Then

        Look for a span with class="section_anchor" and data-label containing "Player Stats" in the format
        second team name Player Stats e.g. Arsenal Player Stats
        
        Navigate to that section to find the player statistics tables
        
        Look for tables with columns including "npxG" and "xAG"
        
        Extract ALL player names and their npxG and xAG values (do not truncate the list)
        
        Return as JSON with player name, npxG, and xAG for each player from both teams
        
        Make sure to include ALL players, not just the first few
        """,
        llm=ChatOpenAI(model="gpt-4.1"),
    )
    
    print("🤖 Starting browser automation...")
    result = await agent.run()
    
    print("\n" + "="*50)
    print("📊 EXTRACTED DATA:")
    print("="*50)
    
    # Handle the new API structure
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
            print(final_result.extracted_content)
            
            # Save to permanent file
            with open('fbref_player_data.json', 'w') as f:
                f.write(final_result.extracted_content)
            print("\n💾 Data saved to fbref_player_data.json")
        else:
            print("No extracted content found")
    except Exception as e:
        print(f"Error processing result: {e}")
        print("Raw result:", result)
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_fbref())
