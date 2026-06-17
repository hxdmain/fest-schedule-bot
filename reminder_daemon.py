#!/usr/bin/env python3
"""
Runs continuously, firing mesh reminders 60 minutes before and at showtime
for every artist on the watchlist.
"""

import json
import os
import time
import requests
from datetime import datetime, timedelta

DATA_DIR = "/home/vanpi/meshmonitor/scripts"
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule.json")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
FIRED_FILE = os.path.join(DATA_DIR, "fired.json")

MESHMONITOR_URL = os.environ.get("MESHMONITOR_URL", "http://localhost:5000")
MESHMONITOR_TOKEN = os.environ.get("MESHMONITOR_TOKEN", "")
MESHMONITOR_SOURCE = os.environ.get("MESHMONITOR_SOURCE", "default")
CHANNEL = 1

CHECK_INTERVAL = 60  # seconds


def send_message(text):
    url = f"{MESHMONITOR_URL}/api/v1/sources/{MESHMONITOR_SOURCE}/messages"
    headers = {"Authorization": f"Bearer {MESHMONITOR_TOKEN}", "Content-Type": "application/json"}
    try:
        requests.post(url, json={"text": text, "channel": CHANNEL}, headers=headers, timeout=10)
        print(f"[{datetime.now().strftime('%H:%M')}] SENT: {text}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M')}] ERROR sending message: {e}")


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else []
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_show_datetime(entry):
    """Return aware datetime for a show entry, handling post-midnight times."""
    date = datetime.strptime(entry["date"], "%Y-%m-%d")
    h, m = map(int, entry["start"].split(":"))
    # Times < 06:00 on the schedule date are actually next calendar day
    if h < 6:
        date += timedelta(days=1)
    return date.replace(hour=h, minute=m, second=0, microsecond=0)


def format_reminder(entry, minutes_out):
    h, m = map(int, entry["start"].split(":"))
    dt = get_show_datetime(entry)
    time_str = dt.strftime("%-I:%M%p").lower()
    stage = entry["stage"]
    artist = entry["artist"]
    if minutes_out == 0:
        return f"STARTING NOW: {artist} @ {stage} ({time_str})"
    else:
        return f"1 HR: {artist} @ {stage} {time_str}"


def check_and_fire():
    now = datetime.now().replace(second=0, microsecond=0)
    schedule = load_json(SCHEDULE_FILE)
    watchlist = load_json(WATCHLIST_FILE)
    fired = set(load_json(FIRED_FILE, default=[]))

    for entry in schedule:
        if entry["artist"] not in watchlist:
            continue

        show_dt = get_show_datetime(entry)
        delta = (show_dt - now).total_seconds() / 60

        for target_minutes, label in [(60, "1hr"), (0, "now")]:
            fire_key = f"{entry['artist']}|{entry['date']}|{entry['start']}|{label}"
            if fire_key in fired:
                continue
            # Fire within a 1-minute window of the target
            if abs(delta - target_minutes) < 1:
                msg = format_reminder(entry, target_minutes)
                send_message(msg)
                fired.add(fire_key)

    save_json(FIRED_FILE, list(fired))


def main():
    print(f"EF reminder daemon started. Checking every {CHECK_INTERVAL}s.")
    while True:
        check_and_fire()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
