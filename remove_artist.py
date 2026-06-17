#!/usr/bin/env python3
"""
MeshMonitor Auto Responder script.
Trigger pattern: remove {artist:.+}
Removes an artist from the watchlist.
"""

import os
import json
from difflib import get_close_matches

DATA_DIR = "/data/scripts"
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def respond(data):
    print(json.dumps(data))


def main():
    query = os.environ.get("PARAM_artist", "").strip()
    if not query:
        respond({"response": "Usage: remove <artist name>"})
        return

    watchlist = load_json(WATCHLIST_FILE)
    query_lower = query.lower()

    # Exact match first
    match = next((a for a in watchlist if a.lower() == query_lower), None)

    # Substring match
    if not match:
        matches = [a for a in watchlist if query_lower in a.lower()]
        if len(matches) == 1:
            match = matches[0]

    # Fuzzy fallback
    if not match:
        close = get_close_matches(query, watchlist, n=1, cutoff=0.6)
        match = close[0] if close else None

    if not match:
        respond({"response": f"'{query}' not found on watchlist."})
        return

    watchlist.remove(match)
    save_json(WATCHLIST_FILE, watchlist)
    respond({"response": f"Removed: {match}"})


if __name__ == "__main__":
    main()
