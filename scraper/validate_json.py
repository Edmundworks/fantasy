#!/usr/bin/env python3
"""
Simple script to validate the extracted match data
"""
import json
import os

def validate_match_data():
    json_file = 'premier_league_matches_2024_2025.json'
    
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        print("Run matchreports.py first!")
        return False
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print("="*60)
        print("📊 MATCH DATA VALIDATION")
        print("="*60)
        
        # Basic validation
        print(f"✅ JSON file loaded successfully")
        print(f"📊 Total matches: {len(data)}")
        
        if len(data) == 0:
            print("❌ No matches found in data")
            return False
            
        # Check first match structure
        first_match = data[0]
        required_fields = ['gameweek', 'home_team', 'away_team', 'match_report_url']
        
        print(f"\n🔍 Sample match (first entry):")
        print(f"   {json.dumps(first_match, indent=2)}")
        
        missing_fields = []
        for field in required_fields:
            if field not in first_match:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print(f"✅ All required fields present")
        
        # Count matches with reports vs without
        with_reports = sum(1 for match in data if match.get('match_report_url') and match['match_report_url'] != 'null')
        without_reports = len(data) - with_reports
        
        print(f"\n📈 Report Status:")
        print(f"   Matches with reports: {with_reports}")
        print(f"   Matches without reports: {without_reports}")
        
        # Check gameweek distribution
        gameweeks = {}
        for match in data:
            gw = match.get('gameweek', 'unknown')
            gameweeks[gw] = gameweeks.get(gw, 0) + 1
        
        print(f"\n📅 Gameweek Distribution:")
        for gw in sorted(gameweeks.keys()):
            print(f"   GW {gw}: {gameweeks[gw]} matches")
        
        # Expected: 38 gameweeks × 10 matches = 380 total
        expected_total = 380
        if len(data) == expected_total:
            print(f"\n✅ Perfect! Found exactly {expected_total} matches as expected")
        else:
            print(f"\n⚠️  Expected {expected_total} matches, found {len(data)}")
            if len(data) < expected_total:
                print("   Possible issues: incomplete extraction, rate limiting")
            
        print("="*60)
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        print("The extracted data might not be valid JSON")
        
        # Show first few lines of the file for debugging
        with open(json_file, 'r') as f:
            content = f.read()[:500]
            print(f"\nFirst 500 characters of file:")
            print(content)
        return False
    
    except Exception as e:
        print(f"❌ Error validating data: {e}")
        return False

if __name__ == "__main__":
    validate_match_data()