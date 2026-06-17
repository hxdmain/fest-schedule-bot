#!/usr/bin/env python3
"""
MeshMonitor Auto Responder script.
Trigger pattern: when {artist:.+}
Looks up any artist on the full schedule.
"""

import os
import json
from difflib import get_close_matches
from datetime import datetime, timedelta

DATA_DIR = "/data/scripts"
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.json")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def find_artist(query, schedule):
    names = [e["artist"] for e in schedule]
    query_lower = query.lower()
    for name in names:
        if name.lower() == query_lower:
            return name
    matches = [n for n in names if query_lower in n.lower()]
    if matches:
        return matches[0]
    close = get_close_matches(query, names, n=1, cutoff=0.6)
    return close[0] if close else None


def format_slot(entry):
    date = datetime.strptime(entry["date"], "%Y-%m-%d")
    h, m = map(int, entry["start"].split(":"))
    if h < 6:
        date += timedelta(days=1)
    day = date.strftime("%a")
    start = datetime.strptime(entry["start"], "%H:%M").strftime("%-I:%M%p").lower()
    end = datetime.strptime(entry["end"], "%H:%M").strftime("%-I:%M%p").lower()
    return f"{entry['stage']} | {day} {start}-{end}"


def respond(data):
    print(json.dumps(data))


def main():
    query = os.environ.get("PARAM_artist", "").strip()
    if not query:
        respond({"response": "Usage: when <artist name>"})
        return

    schedule = load_json(SCHEDULE_FILE)
    artist = find_artist(query, schedule)

    if not artist:
        respond({"response": f"'{query}' not found on schedule."})
        return

    slots = [e for e in schedule if e["artist"] == artist]
    lines = [f"{artist}:"] + [f"  {format_slot(s)}" for s in slots]
    respond({"response": " | ".join([artist] + [format_slot(s) for s in slots])})


if __name__ == "__main__":
    main()
