import json
import os
from typing import Dict, Tuple

BASE_DIR = os.path.dirname(__file__)
APPEAR_NORM = os.path.join(BASE_DIR, 'appearance_data_normalized.json')
APPEAR_RAW = os.path.join(BASE_DIR, 'appearance_data.json')
OUTPUT_JSON = os.path.join(BASE_DIR, 'players_from_appearances.json')

TEAM_ALIASES = {
    'Manchester Utd': 'Manchester United',
    'Man Utd': 'Manchester United',
    'West Ham Utd': 'West Ham',
    'Brighton & Hove Albion': 'Brighton and Hove Albion',
    'Wolves': 'Wolverhampton Wanderers',
    'Newcastle Utd': 'Newcastle United',
}


def normalize_team(name: str) -> str:
    if not name:
        return name
    n = name.replace('Table', '').strip()
    while '  ' in n:
        n = n.replace('  ', ' ')
    if n in TEAM_ALIASES:
        return TEAM_ALIASES[n]
    n = n.replace(' Utd', ' United')
    return n


def load_rows():
    path = APPEAR_NORM if os.path.exists(APPEAR_NORM) else APPEAR_RAW
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Ensure team normalization if using raw
    for r in data:
        r['teamName'] = normalize_team(r.get('teamName', ''))
    return data


def main():
    rows = load_rows()

    # Aggregate by (playerName, teamName)
    agg: Dict[Tuple[str, str], Dict] = {}
    for r in rows:
        player = r.get('playerName')
        team = normalize_team(r.get('teamName', ''))
        if not player or not team:
            continue
        key = (player, team)
        if key not in agg:
            agg[key] = {
                'playerName': player,
                'teamName': team,
                'totalAppearances': 0,
                'totalMinutes': 0,
                'totalNpxG': 0.0,
                'totalXAG': 0.0,
            }
        agg[key]['totalAppearances'] += 1 if r.get('in_squad') else 0
        minutes = r.get('minutes_played')
        if isinstance(minutes, int):
            agg[key]['totalMinutes'] += minutes
        npxg = r.get('npXg')
        if isinstance(npxg, (int, float)):
            agg[key]['totalNpxG'] += float(npxg)
        xag = r.get('xAG')
        if isinstance(xag, (int, float)):
            agg[key]['totalXAG'] += float(xag)

    # Sort deterministically: by team, then player
    players = list(agg.values())
    players.sort(key=lambda x: (x['teamName'], x['playerName']))

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(players, f, indent=2, ensure_ascii=False)

    print(f'Wrote {len(players)} unique players to {OUTPUT_JSON}')


if __name__ == '__main__':
    main()