#!/usr/bin/env python3
"""
MeshMonitor Auto Responder script.
Trigger pattern: list
Returns today's watchlist artists sorted by start time.
Falls back to full watchlist sorted by date/time if no shows today.
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
    stage_short = entry["stage"].replace("The Observatory", "Observ.").replace("Sherwood Court", "Sherwood").replace("Center Stage", "Center").replace("Ranch Arena", "Ranch").replace("Honeycomb", "Honey").replace("Tripolee", "Tripolee")
    return f"{entry['artist']} @ {stage_short} {time_str}"


def respond(data):
    print(json.dumps(data))


def main():
    schedule = load_json(SCHEDULE_FILE)
    watchlist = load_json(WATCHLIST_FILE)

    if not watchlist:
        respond({"response": "Watchlist is empty. Type: add <artist>"})
        return

    now = datetime.now()

    # Determine which day to show
    # During festival: show today's remaining + upcoming shows
    # Outside festival: show all days
    festival_day = None
    for i in range(4):
        day = FESTIVAL_START + timedelta(days=i)
        # Festival day runs from ~noon to ~4am next morning
        day_start = day.replace(hour=12, minute=0)
        day_end = day.replace(hour=23, minute=59) + timedelta(hours=4)
        if day_start <= now <= day_end:
            festival_day = day
            break

    # Build watchlist shows
    watched_shows = [e for e in schedule if e["artist"] in watchlist]
    watched_shows.sort(key=get_show_datetime)

    if festival_day:
        # Filter to today's shows (noon to 4am next day)
        day_start = festival_day.replace(hour=12, minute=0)
        day_end = (festival_day + timedelta(days=1)).replace(hour=4, minute=0)
        todays = [e for e in watched_shows if day_start <= get_show_datetime(e) <= day_end]
        upcoming = [e for e in todays if get_show_datetime(e) >= now]
        label = festival_day.strftime("%a")

        if not todays:
            respond({"response": f"No watchlist shows today ({label}). Type: list all"})
            return

        lines = [f"[{label} watchlist]"] + [format_entry(e) for e in todays]
    else:
        # Pre/post festival — show all by day
        lines = ["[Full watchlist]"] + [
            f"{get_show_datetime(e).strftime('%a')} - {format_entry(e)}"
            for e in watched_shows
        ]

    # Pack into up to 3 messages of ~190 chars each
    messages = []
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
        messages[-1] = messages[-1][:180] + "…"

    respond({"responses": messages} if len(messages) > 1 else {"response": messages[0]})


if __name__ == "__main__":
    main()
