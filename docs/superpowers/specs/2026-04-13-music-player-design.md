# Music Player with Jingle Crossfade — Design Spec

## Overview

Desktop music player for looping background music with manual jingle triggering via crossfade. Built with Python, PyQt6 (GUI), and pygame.mixer (audio). Compiles to standalone app via PyInstaller.

## Architecture

Three layers:

### AudioEngine (`audio_engine.py`)
Wrapper over pygame.mixer. Two logical stereo channels:
- `music_channel` (Channel 0) — background music
- `jingle_channel` (Channel 1) — jingles

Responsibilities:
- Play/stop/pause/unpause on each channel
- Fade out via `pygame.mixer.Channel.fadeout()`
- Fade in via QTimer — incrementally raises volume from 0 to target over configured duration
- Volume control per channel
- Status queries (is playing, current position)

### PlaybackController (`playback_controller.py`)
Orchestrates playback logic. Knows about playlists, track order, repeat modes, per-jingle volumes.

Jingle scenario:
1. User triggers jingle
2. If background music is playing:
   - Start fade out of background music (configured duration)
   - Immediately start jingle at full (per-jingle) volume — does NOT wait for fade out to finish
   - After fade out completes — pause background music (so it doesn't advance)
   - After jingle finishes — unpause background music and fade it in (configured duration)
3. If background music is not playing:
   - Just play the jingle

Jingle queue: if another jingle is triggered during playback, it queues. Fade in of background music happens only after the last jingle in queue finishes.

Background music modes:
- Playlist loop — after track ends, play next; after last, play first
- Single track loop — current track repeats indefinitely
- Mode switch applies after current track ends
- Clicking a track in the list switches playback to it

### GUI (`gui/`)
PyQt6 widgets. Display and input only — all logic in controller. Communication via Qt signals/slots.

## GUI Layout

```
+-------------------------+-------------------------+
|   BACKGROUND MUSIC      |   JINGLES               |
|                         |                         |
|  [Play] [Stop]          |                         |
|  ( ) Playlist loop      |                         |
|  ( ) Single track loop  |                         |
|                         |                         |
|  +-------------------+  |  +-------------------+  |
|  | track1.mp3        |  |  | jingle1.mp3 [==] |  |
|  | track2.wav        |  |  | jingle2.wav [==] |  |
|  | track3.mp3        |  |  | jingle3.mp3 [==] |  |
|  +-------------------+  |  +-------------------+  |
|   drag & drop here      |   drag & drop here      |
|                         |                         |
|  Volume: [=========]    |                         |
|                         |                         |
+-------------------------+-------------------------+
|  Fade Out: [====] 2.0s    Fade In: [====] 2.0s   |
+---------------------------------------------------+
```

- Left panel: background track list (drag & drop to add files and reorder), repeat mode radio buttons, Play/Stop, volume slider
- Right panel: jingle list (drag & drop to add and reorder), per-jingle volume slider next to each item. Double-click to trigger jingle.
- Bottom bar: Fade Out slider (0–5 sec), Fade In slider (0–5 sec)
- Currently playing track/jingle is highlighted in list

## Playback Details

### Background Music
- Supported formats: MP3, WAV
- Volume: single master slider for all background tracks (0–100%)
- On track end: auto-advance per repeat mode
- Click on track: switch to it immediately

### Jingles
- Supported formats: MP3, WAV
- Volume: individual slider per jingle (0–100%)
- Trigger: double-click on jingle in list
- Plays immediately at configured volume — no fade applied to jingle itself
- Queue: subsequent triggers queue, play sequentially

### Crossfade Behavior
- Fade Out (0–5 sec): applied to background music when jingle starts. Background fades from current volume to 0.
- Fade In (0–5 sec): applied to background music after last jingle ends. Background fades from 0 to configured volume.
- Jingle always starts instantly, simultaneously with the beginning of fade out.
- If fade values are 0: background cuts immediately, jingle plays, background resumes immediately.

## State Persistence

JSON file `player_state.json` next to the executable:

```json
{
  "background": {
    "files": ["/path/to/track1.mp3", "/path/to/track2.wav"],
    "volume": 0.8,
    "repeat_mode": "playlist"
  },
  "jingles": {
    "files": [
      {"path": "/path/to/jingle1.mp3", "volume": 0.7},
      {"path": "/path/to/jingle2.wav", "volume": 1.0}
    ]
  },
  "fade_out": 2.0,
  "fade_in": 2.0
}
```

- Auto-saved on every change (add/remove tracks, reorder, volume change, fade change)
- Loaded on startup; missing or corrupt file = start with empty state
- Files that no longer exist on disk are silently skipped on load

## Project Structure

```
player/
├── main.py                  # Entry point
├── audio_engine.py          # pygame.mixer wrapper
├── playback_controller.py   # Playback logic, playlists, jingle scenario
├── state_manager.py         # JSON state load/save
├── gui/
│   ├── main_window.py       # Main window, two-panel layout + bottom bar
│   ├── track_list.py        # Track list widget with drag & drop and reordering
│   └── jingle_list.py       # Jingle list widget with per-item volume sliders
├── requirements.txt         # PyQt6, pygame
└── build.py                 # PyInstaller build script
```

## Tech Stack

- **Python 3.11+**
- **PyQt6** — GUI framework
- **pygame.mixer** — audio playback (stereo, two logical channels)
- **PyInstaller** — compilation to standalone app
- **Cross-platform** — macOS, Windows, Linux
