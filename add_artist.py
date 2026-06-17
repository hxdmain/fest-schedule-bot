#!/usr/bin/env python3
"""
MeshMonitor Auto Responder script.
Trigger pattern: add {artist:.+}
Adds an artist to the watchlist and warns of any time conflicts.
"""

import os
import json
from difflib import get_close_matches
from datetime import datetime, timedelta

DATA_DIR = "/data/scripts"
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.json")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


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


def get_show_datetime(entry, field="start"):
    date = datetime.strptime(entry["date"], "%Y-%m-%d")
    h, m = map(int, entry[field].split(":"))
    if h < 6:
        date += timedelta(days=1)
    return date.replace(hour=h, minute=m)


def slots_overlap(a, b):
    a_start = get_show_datetime(a, "start")
    a_end = get_show_datetime(a, "end")
    b_start = get_show_datetime(b, "start")
    b_end = get_show_datetime(b, "end")
    return a_start < b_end and b_start < a_end


def format_slot(entry):
    date = datetime.strptime(entry["date"], "%Y-%m-%d")
    h, m = map(int, entry["start"].split(":"))
    if h < 6:
        date += timedelta(days=1)
    day = date.strftime("%a")
    time_str = datetime.strptime(entry["start"], "%H:%M").strftime("%-I:%M%p").lower()
    return f"{entry['stage']} | {day} {time_str}"


def respond(data):
    print(json.dumps(data))


def main():
    query = os.environ.get("PARAM_artist", "").strip()
    if not query:
        respond({"response": "Usage: add <artist name>"})
        return

    schedule = load_json(SCHEDULE_FILE)
    watchlist = load_json(WATCHLIST_FILE)

    artist = find_artist(query, schedule)
    if not artist:
        respond({"response": f"'{query}' not found on schedule. Check spelling?"})
        return

    slots = [e for e in schedule if e["artist"] == artist]
    slot_str = " / ".join(format_slot(s) for s in slots)

    if artist in watchlist:
        respond({"response": f"{artist} already on watchlist. {slot_str}"})
        return

    # Check for conflicts with existing watchlist
    watched_slots = [e for e in schedule if e["artist"] in watchlist]
    conflicts = []
    for new_slot in slots:
        for existing in watched_slots:
            if slots_overlap(new_slot, existing):
                conflicts.append(existing["artist"])

    watchlist.append(artist)
    save_json(WATCHLIST_FILE, watchlist)

    if conflicts:
        conflict_str = ", ".join(set(conflicts))
        respond({"response": f"Added: {artist} @ {slot_str} | ⚠️ Conflict: {conflict_str}"})
    else:
        respond({"response": f"Added: {artist} @ {slot_str}"})


if __name__ == "__main__":
    main()
