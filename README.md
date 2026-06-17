# EF Bot — Electric Forest Mesh Schedule Bot

A Meshtastic mesh bot for Electric Forest (or any multi-day festival) that runs on a Raspberry Pi via MeshMonitor. Anyone on your private mesh channel can look up artists, manage a shared watchlist, and receive automatic reminders before shows start.

---

## What It Does

- **Add artists** to a shared watchlist by typing in chat
- **Conflict detection** — warns you when a new artist overlaps with someone already on the watchlist
- **Automatic reminders** — fires 1 hour before and at showtime for every watched artist
- **Look up any artist** on the full schedule without adding them
- **List today's shows** sorted by start time
- **Remove artists** from the watchlist
- **Daily blast** — sends the full day's watchlist every morning at 10am

All commands work over Meshtastic mesh — no internet, no cell service required.

---

## Hardware & Software Requirements

- Raspberry Pi (any model with Wi-Fi)
- Meshtastic radio node connected to the Pi's local network via TCP
- [MeshMonitor](https://meshmonitor.org) running in Docker
- A private Meshtastic channel shared across your group's devices

---

## Setup

### 1. Install MeshMonitor with Docker

Create `docker-compose.yml`:

```yaml
services:
  meshmonitor:
    image: ghcr.io/yeraze/meshmonitor:latest
    container_name: meshmonitor
    ports:
      - "3001:3001"
    restart: unless-stopped
    volumes:
      - /path/to/meshmonitor/data:/data
      - /path/to/meshmonitor/scripts:/data/scripts
    environment:
      - NODE_ENV=development
      - PORT=3001
      - TZ=America/New_York
      - ALLOWED_ORIGINS=*
      - MESHTASTIC_NODE_IP=YOUR_RADIO_IP
      - MESHTASTIC_TCP_PORT=4403
```

```bash
docker compose up -d
```

> **Important:** Set the Heartbeat to 30 seconds on your MeshMonitor source (Settings → Sources → Edit) to prevent TCP connection drops through Docker NAT.

### 2. Copy Bot Files

Copy everything from this folder into your MeshMonitor scripts directory:

```bash
cp *.py /path/to/meshmonitor/scripts/
cp schedule.json watchlist.json /path/to/meshmonitor/scripts/
```

### 3. Build Your Schedule

Edit `schedule.json` with your festival's timetable. Each entry:

```json
{ "artist": "Artist Name", "stage": "Stage Name", "date": "2026-06-25", "start": "21:30", "end": "23:00" }
```

- Use 24-hour time
- Post-midnight sets (e.g. `01:30`) stay on the **previous calendar date** — the bot handles the day rollover automatically
- `date` is the calendar date the festival day *starts*, not when the set plays

### 4. Pre-populate the Watchlist

Edit `watchlist.json` with any artists you want tracked from day one:

```json
["GRiZ", "ILLENIUM", "Chris Lake"]
```

### 5. Wire Up MeshMonitor Auto Responders

In MeshMonitor UI → **Settings → Automation → Auto Responder**, create one trigger per command:

| Trigger Pattern | Script | Channel |
|---|---|---|
| `add {artist:.+}` | `add_artist.py` | your channel # |
| `remove {artist:.+}` | `remove_artist.py` | your channel # |
| `when {artist:.+}` | `when_artist.py` | your channel # |
| `list` | `list_artists.py` | your channel # |

### 6. Set Up the Daily Blast (Optional)

In MeshMonitor UI → **Settings → Automation → Timer Triggers**, add:

- **Cron:** `0 10 25-28 6 *` (10am on each festival day — adjust dates/time to your event)
- **Script:** `daily_blast.py`
- **Channel:** your channel #

Update `daily_blast.py` with your MeshMonitor API token and source ID:

```python
MESHMONITOR_TOKEN = "your_token_here"
MESHMONITOR_SOURCE = "your_source_id_here"
```

### 7. Install the Reminder Daemon

The reminder daemon runs as a systemd service outside of Docker and fires reminders via the MeshMonitor API.

```bash
# Copy the service file
sudo cp ef-reminders.service /etc/systemd/system/

# Edit config.env with your credentials
nano config.env

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now ef-reminders
```

`config.env`:
```
MESHMONITOR_URL=http://localhost:3001
MESHMONITOR_TOKEN=your_token_here
MESHMONITOR_SOURCE=your_source_id_here
```

To find your source ID:
```bash
curl -s -H "Authorization: Bearer YOUR_TOKEN" http://localhost:3001/api/v1/sources
```

---

## Commands

All commands are sent as plain text messages on your private Meshtastic channel.

| Command | What it does | Example |
|---|---|---|
| `add <artist>` | Add artist to watchlist, warns of conflicts | `add GRiZ` |
| `remove <artist>` | Remove artist from watchlist | `remove GRiZ` |
| `when <artist>` | Look up any artist on the full schedule | `when Kaskade` |
| `list` | Today's watchlist sorted by time | `list` |

Commands are case-insensitive and use fuzzy matching — `add griz`, `Add GRiZ`, and `add gri` all work.

---

## Reminders

The reminder daemon checks every 60 seconds and sends two alerts per watched artist:

- **1 hour before:** `1 HR: GRiZ @ Ranch Arena 12:00am`
- **At showtime:** `STARTING NOW: GRiZ @ Ranch Arena`

Each reminder fires exactly once — no duplicates even if the daemon restarts.

---

## Files

| File | Purpose |
|---|---|
| `schedule.json` | Full festival timetable |
| `watchlist.json` | Artists your group is tracking (shared, updated by bot) |
| `fired.json` | Tracks which reminders have already been sent |
| `add_artist.py` | Handles `add` command with conflict detection |
| `remove_artist.py` | Handles `remove` command |
| `when_artist.py` | Handles `when` command |
| `list_artists.py` | Handles `list` command |
| `daily_blast.py` | Timer-triggered daily schedule broadcast |
| `reminder_daemon.py` | Background service for 1hr/showtime reminders |
| `config.env` | MeshMonitor credentials for the reminder daemon |
| `ef-reminders.service` | systemd unit for the reminder daemon |

---

## Adapting for Other Festivals

1. Replace `schedule.json` with your festival's timetable
2. Update `FESTIVAL_START` / `FESTIVAL_END` in `list_artists.py` and `daily_blast.py`
3. Update the Timer Trigger cron expression for your festival dates
4. Clear `watchlist.json` and `fired.json` before the event

---

## Notes

- Meshtastic has a 200-byte message limit. The bot auto-splits long responses (e.g. `list`) across multiple messages, up to 3 parts (~600 bytes total).
- The `watchlist.json` and `fired.json` files are shared state — all group members' `add`/`remove` commands update the same list.
- Artist matching is fuzzy — partial names and common misspellings will usually resolve correctly.
