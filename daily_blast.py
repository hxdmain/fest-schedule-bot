#!/usr/bin/env python3
"""
MeshMonitor Timer Trigger script.
Set cron to: 0 10 25-28 6 *  (10am Jun 25-28)
Select channel 1 in the Timer UI.
MeshMonitor sends the JSON responses to the configured channel.
"""

import os
import json
from datetime import datetime, timedelta

DATA_DIR = "/data/scripts"
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.json")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")

FESTIVAL_START = datetime(2026, 6, 25)
FESTIVAL_END = datetime(2026, 6, 28)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def get_show_datetime(entry):
    date = datetime.strptime(entry["date"], "%Y-%m-%d")
    h, m = map(int, entry["start"].split(":"))
    if h < 6:
        date += timedelta(days=1)
    return date.replace(hour=h, minute=m)


def format_entry(entry):
    dt = get_show_datetime(entry)
    time_str = dt.strftime("%-I:%M%p").lower()
    stage_short = (entry["stage"]
        .replace("The Observatory", "Observ.")
        .replace("Sherwood Court", "Sherwood")
        .replace("Center Stage", "Center")
        .replace("Ranch Arena", "Ranch")
        .replace("Honeycomb", "Honey"))
    return f"{entry['artist']} @ {stage_short} {time_str}"


def main():
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if not (FESTIVAL_START <= today <= FESTIVAL_END):
        print(json.dumps({"response": "No festival today."}))
        return

    schedule = load_json(SCHEDULE_FILE)
    watchlist = load_json(WATCHLIST_FILE)

    if not watchlist:
        print(json.dumps({"response": "Watchlist is empty. Type: add <artist>"}))
        return

    day_start = today.replace(hour=12)
    day_end = (today + timedelta(days=1)).replace(hour=4)

    watched = [e for e in schedule if e["artist"] in watchlist]
    watched.sort(key=get_show_datetime)
    todays = [e for e in watched if day_start <= get_show_datetime(e) <= day_end]

    if not todays:
        print(json.dumps({"response": f"No watchlist shows today ({now.strftime('%A')})."}))
        return

    day_label = now.strftime("%A, %b %-d")
    header = f"EF {day_label} watchlist ({len(todays)} shows):"

    # Pack into messages of ~190 chars each, max 3
    lines = [format_entry(e) for e in todays]
    messages = [header]
    current = ""
    for line in lines:
        chunk = (current + "\n" + line).strip() if current else line
        if len(chunk) > 190:
            messages.append(current)
            current = line
        else:
            current = chunk
    if current:
        messages.append(current)

    if len(messages) > 3:
        messages = messages[:3]
        messages[-1] = messages[-1][:185] + "…"

    print(json.dumps({"responses": messages}))


if __name__ == "__main__":
    main()
