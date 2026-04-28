from api.picks_service import get_pick_stats, get_todays_picks
import json

picks = get_todays_picks()
nantes = [p for p in picks if "Nantes" in p["match"]]
if nantes:
    pick_id = nantes[0]["id"]
    stats = get_pick_stats(pick_id)
    print("NANTES STATS:", json.dumps(stats, indent=2))
else:
    print("Nantes not found. Printing first pick stats.")
    if picks:
        stats = get_pick_stats(picks[0]["id"])
        print("FIRST PICK STATS:", json.dumps(stats, indent=2))
