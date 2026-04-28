import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.picks_service import get_todays_picks, get_pick_stats

picks = get_todays_picks()
empty_count = 0
for pick in picks:
    stats = get_pick_stats(pick["id"])
    if not stats:
        print(f"FAILED: {pick['match']} (stats returned None)")
        empty_count += 1
        continue
    
    h_len = len(stats["home_stats"]["last_5"])
    a_len = len(stats["away_stats"]["last_5"])
    
    if h_len == 0 or a_len == 0:
        print(f"EMPTY STATS: {pick['match']} -> Home: {h_len}, Away: {a_len}")
        empty_count += 1

print(f"Total picks: {len(picks)}, Empty stats: {empty_count}")
