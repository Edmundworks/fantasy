#!/usr/bin/env python3
"""
Extract complete HTML from a FBref match report page to understand structure
"""
import requests
from bs4 import BeautifulSoup
import json

def extract_match_report_html():
    # Sample match report URL
    url = "https://fbref.com/en/matches/de7298df/Fulham-Newcastle-United-September-21-2024-Premier-League"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"🔍 Fetching match report: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        print(f"✅ Successfully fetched page ({len(response.text)} characters)")
        
        # Save full HTML
        with open('match_report_sample.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"💾 Saved complete HTML to: match_report_sample.html")
        
        # Parse and analyze structure
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print("\n" + "="*60)
        print("📊 HTML STRUCTURE ANALYSIS")
        print("="*60)
        
        # Find key elements
        analysis = {}
        
        # Match info
        match_info = soup.find('h1')
        if match_info:
            analysis['match_title'] = match_info.get_text().strip()
            print(f"🏆 Match: {analysis['match_title']}")
        
        # Score
        score_divs = soup.find_all('div', class_='score')
        if score_divs:
            scores = [div.get_text().strip() for div in score_divs]
            analysis['scores'] = scores
            print(f"⚽ Scores found: {scores}")
        
        # Tables (likely contain player stats)
        tables = soup.find_all('table')
        print(f"📊 Total tables found: {len(tables)}")
        
        # Look for specific table types
        table_types = []
        for i, table in enumerate(tables):
            table_id = table.get('id', 'no-id')
            table_class = table.get('class', [])
            
            # Check for stats-related tables
            if any(keyword in table_id.lower() for keyword in ['stats', 'summary', 'keeper', 'passing', 'defense']):
                table_types.append({
                    'index': i,
                    'id': table_id,
                    'class': table_class,
                    'rows': len(table.find_all('tr'))
                })
        
        analysis['stats_tables'] = table_types
        print(f"📈 Stats tables found: {len(table_types)}")
        
        for table in table_types[:5]:  # Show first 5
            print(f"   - Table {table['index']}: {table['id']} ({table['rows']} rows)")
        
        # Look for comments (FBref often hides tables in comments)
        comments = soup.find_all(string=lambda text: isinstance(text, BeautifulSoup) or (hasattr(text, 'strip') and '<table' in str(text)))
        comment_tables = []
        
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and '<table' in text):
            if 'stats' in str(comment).lower():
                comment_tables.append(str(comment)[:100] + '...')
        
        analysis['comment_tables'] = len(comment_tables)
        print(f"💬 Tables in comments: {len(comment_tables)}")
        
        # Goals/events
        goal_events = soup.find_all('div', class_=['event', 'goal'])
        analysis['goal_events'] = len(goal_events)
        print(f"⚽ Goal events found: {len(goal_events)}")
        
        # Formation diagrams
        formations = soup.find_all('div', class_=['formation', 'lineup'])
        analysis['formations'] = len(formations)
        print(f"📋 Formation/lineup elements: {len(formations)}")
        
        # Save analysis
        with open('match_report_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved analysis to: match_report_analysis.json")
        
        # Sample some table headers to understand structure
        print("\n" + "="*60)
        print("📊 SAMPLE TABLE HEADERS")
        print("="*60)
        
        for i, table in enumerate(tables[:3]):  # First 3 tables
            headers = table.find_all('th')
            if headers:
                header_texts = [th.get_text().strip() for th in headers[:10]]  # First 10 headers
                print(f"\nTable {i}: {header_texts}")
        
        print(f"\n✅ Complete analysis saved!")
        print(f"📁 Files created:")
        print(f"   - match_report_sample.html ({len(response.text)} chars)")
        print(f"   - match_report_analysis.json")
        
    except requests.RequestException as e:
        print(f"❌ Error fetching page: {e}")
    except Exception as e:
        print(f"❌ Error processing page: {e}")

if __name__ == "__main__":
    extract_match_report_html()