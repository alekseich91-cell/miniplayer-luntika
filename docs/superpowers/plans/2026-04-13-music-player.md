# Music Player Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop music player that loops background music and plays jingles with crossfade via manual trigger.

**Architecture:** Three-layer: AudioEngine (pygame.mixer wrapper), PlaybackController (orchestration), GUI (PyQt6). State persisted as JSON.

**Tech Stack:** Python 3.11+, PyQt6, pygame, PyInstaller, pytest

**Spec Deviation:** The spec mentions two `pygame.mixer.Channel` instances. The implementation uses `pygame.mixer.music` for background (better MP3 streaming, built-in pause/unpause) and `pygame.mixer.Channel(0)` for jingles (short clips loaded into memory). Functionally equivalent, more robust for MP3.

---

### File Structure

| File | Responsibility |
|------|---------------|
| `main.py` | Entry point — creates app, wires components, runs event loop |
| `audio_engine.py` | pygame.mixer wrapper — music stream, jingle channel, fade via QTimer |
| `playback_controller.py` | Playlist logic, repeat modes, jingle scenario with queue |
| `state_manager.py` | PlayerState dataclass + JSON load/save |
| `gui/__init__.py` | Empty package init |
| `gui/main_window.py` | Main window — two-panel layout + bottom fade bar, signal wiring |
| `gui/track_list.py` | QListWidget subclass — drag & drop files, internal reorder, delete |
| `gui/jingle_list.py` | QListWidget subclass — drag & drop files, per-item volume sliders, double-click trigger |
| `tests/__init__.py` | Empty |
| `tests/test_state_manager.py` | StateManager unit tests |
| `tests/test_playback_controller.py` | PlaybackController unit tests with mocked engine |
| `requirements.txt` | Dependencies |
| `build.py` | PyInstaller build script |

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `main.py` (stub)
- Create: `gui/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
PyQt6>=6.6.0
pygame>=2.5.0
pyinstaller>=6.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Create directory structure and stubs**

Create directories `gui/` and `tests/`, with empty `__init__.py` in each.

Create `main.py`:

```python
import sys
from PyQt6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Music Player")
    # Components will be wired here in Task 8
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Install dependencies and verify**

Run: `pip install -r requirements.txt`
Then: `python -c "import PyQt6; import pygame; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

Stage `requirements.txt`, `main.py`, `gui/__init__.py`, `tests/__init__.py` and commit with message `feat: project scaffold with dependencies`.

---

### Task 2: StateManager + Tests

**Files:**
- Create: `state_manager.py`
- Create: `tests/test_state_manager.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_state_manager.py`:

```python
import json
import os
import pytest
from state_manager import StateManager, PlayerState, JingleEntry


@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / "player_state.json")


class TestStateManager:
    def test_load_missing_file_returns_default(self, state_path):
        sm = StateManager(state_path)
        state = sm.load()
        assert state.background_files == []
        assert state.background_volume == 0.8
        assert state.repeat_mode == "playlist"
        assert state.jingles == []
        assert state.fade_out == 2.0
        assert state.fade_in == 2.0

    def test_save_and_load_roundtrip(self, state_path):
        sm = StateManager(state_path)
        state = PlayerState(
            background_files=["/music/track1.mp3", "/music/track2.wav"],
            background_volume=0.6,
            repeat_mode="single",
            jingles=[
                JingleEntry(path="/jingles/j1.mp3", volume=0.7),
                JingleEntry(path="/jingles/j2.wav", volume=1.0),
            ],
            fade_out=3.0,
            fade_in=1.5,
        )
        sm.save(state)
        loaded = sm.load()
        assert loaded.background_files == state.background_files
        assert loaded.background_volume == state.background_volume
        assert loaded.repeat_mode == state.repeat_mode
        assert len(loaded.jingles) == 2
        assert loaded.jingles[0].path == "/jingles/j1.mp3"
        assert loaded.jingles[0].volume == 0.7
        assert loaded.fade_out == 3.0
        assert loaded.fade_in == 1.5

    def test_load_corrupt_file_returns_default(self, state_path):
        with open(state_path, "w") as f:
            f.write("not json{{{")
        sm = StateManager(state_path)
        state = sm.load()
        assert state.background_files == []

    def test_load_skips_missing_audio_files(self, state_path, tmp_path):
        existing = str(tmp_path / "exists.mp3")
        with open(existing, "w") as f:
            f.write("fake")
        data = {
            "background": {
                "files": [existing, "/gone/missing.mp3"],
                "volume": 0.8,
                "repeat_mode": "playlist",
            },
            "jingles": {
                "files": [
                    {"path": existing, "volume": 0.5},
                    {"path": "/gone/missing.wav", "volume": 1.0},
                ]
            },
            "fade_out": 2.0,
            "fade_in": 2.0,
        }
        with open(state_path, "w") as f:
            json.dump(data, f)
        sm = StateManager(state_path)
        state = sm.load()
        assert state.background_files == [existing]
        assert len(state.jingles) == 1
        assert state.jingles[0].path == existing
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state_manager.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'state_manager'`

- [ ] **Step 3: Implement StateManager**

Create `state_manager.py`:

```python
import json
import os
from dataclasses import dataclass, field


@dataclass
class JingleEntry:
    path: str
    volume: float = 1.0


@dataclass
class PlayerState:
    background_files: list[str] = field(default_factory=list)
    background_volume: float = 0.8
    repeat_mode: str = "playlist"
    jingles: list[JingleEntry] = field(default_factory=list)
    fade_out: float = 2.0
    fade_in: float = 2.0


class StateManager:
    def __init__(self, path: str):
        self._path = path

    def load(self) -> PlayerState:
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return PlayerState()

        try:
            bg = data.get("background", {})
            bg_files = [p for p in bg.get("files", []) if os.path.exists(p)]
            bg_volume = float(bg.get("volume", 0.8))
            repeat_mode = bg.get("repeat_mode", "playlist")

            jingles_data = data.get("jingles", {}).get("files", [])
            jingles = [
                JingleEntry(path=j["path"], volume=float(j.get("volume", 1.0)))
                for j in jingles_data
                if os.path.exists(j.get("path", ""))
            ]

            fade_out = float(data.get("fade_out", 2.0))
            fade_in = float(data.get("fade_in", 2.0))

            return PlayerState(
                background_files=bg_files,
                background_volume=bg_volume,
                repeat_mode=repeat_mode,
                jingles=jingles,
                fade_out=fade_out,
                fade_in=fade_in,
            )
        except (KeyError, TypeError, ValueError):
            return PlayerState()

    def save(self, state: PlayerState) -> None:
        data = {
            "background": {
                "files": state.background_files,
                "volume": state.background_volume,
                "repeat_mode": state.repeat_mode,
            },
            "jingles": {
                "files": [
                    {"path": j.path, "volume": j.volume} for j in state.jingles
                ]
            },
            "fade_out": state.fade_out,
            "fade_in": state.fade_in,
        }
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state_manager.py -v`

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

Stage `state_manager.py` and `tests/test_state_manager.py`, commit with message `feat: StateManager with JSON persistence and tests`.

---

### Task 3: AudioEngine

**Files:**
- Create: `audio_engine.py`

- [ ] **Step 1: Implement AudioEngine**

Create `audio_engine.py`:

```python
import pygame
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class AudioEngine(QObject):
    music_ended = pyqtSignal()
    jingle_ended = pyqtSignal()

    FADE_STEP_MS = 30

    def __init__(self):
        super().__init__()
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        pygame.mixer.set_num_channels(8)
        self._jingle_channel = pygame.mixer.Channel(0)

        self._music_volume = 1.0
        self._current_music_vol = 0.0
        self._music_loaded = False
        self._music_playing = False
        self._music_paused = False
        self._jingle_playing = False
        self._current_jingle_sound = None

        # Fade state
        self._fade_timer = QTimer()
        self._fade_timer.setInterval(self.FADE_STEP_MS)
        self._fade_timer.timeout.connect(self._on_fade_step)
        self._fade_start = 0.0
        self._fade_target = 0.0
        self._fade_step_count = 0
        self._fade_total_steps = 1
        self._fade_callback = None

        # Poll for track/jingle end
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start()

        # Track end event
        self._MUSIC_END = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self._MUSIC_END)

    def play_music(self, path: str) -> None:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(self._music_volume)
        pygame.mixer.music.play()
        self._current_music_vol = self._music_volume
        self._music_loaded = True
        self._music_playing = True
        self._music_paused = False

    def stop_music(self) -> None:
        self._cancel_fade()
        pygame.mixer.music.stop()
        self._music_playing = False
        self._music_paused = False

    def pause_music(self) -> None:
        if self._music_playing and not self._music_paused:
            pygame.mixer.music.pause()
            self._music_paused = True

    def unpause_music(self) -> None:
        if self._music_paused:
            pygame.mixer.music.unpause()
            self._music_paused = False

    def set_music_volume(self, volume: float) -> None:
        self._music_volume = max(0.0, min(1.0, volume))
        if self._music_playing and not self._fade_timer.isActive():
            pygame.mixer.music.set_volume(self._music_volume)
            self._current_music_vol = self._music_volume

    def fade_music_volume(
        self, target: float, duration_sec: float, on_complete=None
    ) -> None:
        self._cancel_fade()
        target = max(0.0, min(1.0, target))

        if duration_sec <= 0:
            pygame.mixer.music.set_volume(target)
            self._current_music_vol = target
            if on_complete:
                on_complete()
            return

        self._fade_start = self._current_music_vol
        self._fade_target = target
        self._fade_step_count = 0
        self._fade_total_steps = max(int(duration_sec * 1000 / self.FADE_STEP_MS), 1)
        self._fade_callback = on_complete
        self._fade_timer.start()

    def is_music_playing(self) -> bool:
        return self._music_playing and not self._music_paused

    def is_music_paused(self) -> bool:
        return self._music_paused

    def play_jingle(self, path: str, volume: float) -> None:
        sound = pygame.mixer.Sound(path)
        self._current_jingle_sound = sound
        self._jingle_channel.set_volume(max(0.0, min(1.0, volume)))
        self._jingle_channel.play(sound)
        self._jingle_playing = True

    def is_jingle_playing(self) -> bool:
        return self._jingle_playing

    def cleanup(self) -> None:
        self._poll_timer.stop()
        self._cancel_fade()
        pygame.mixer.quit()

    def _cancel_fade(self) -> None:
        if self._fade_timer.isActive():
            self._fade_timer.stop()
            self._fade_callback = None

    def _on_fade_step(self) -> None:
        self._fade_step_count += 1
        progress = min(self._fade_step_count / self._fade_total_steps, 1.0)
        vol = self._fade_start + (self._fade_target - self._fade_start) * progress
        pygame.mixer.music.set_volume(vol)
        self._current_music_vol = vol

        if progress >= 1.0:
            self._fade_timer.stop()
            cb = self._fade_callback
            self._fade_callback = None
            if cb:
                cb()

    def _poll_status(self) -> None:
        for event in pygame.event.get():
            if event.type == self._MUSIC_END:
                if self._music_playing and not self._music_paused:
                    self._music_playing = False
                    self.music_ended.emit()

        if self._jingle_playing and not self._jingle_channel.get_busy():
            self._jingle_playing = False
            self.jingle_ended.emit()
```

- [ ] **Step 2: Smoke test**

Run:
```python
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from audio_engine import AudioEngine
e = AudioEngine()
print('AudioEngine created OK')
e.cleanup()
print('Cleanup OK')
"
```

Expected: `AudioEngine created OK` / `Cleanup OK`

- [ ] **Step 3: Commit**

Stage `audio_engine.py`, commit with message `feat: AudioEngine with fade, jingle channel, and status polling`.

---

### Task 4: PlaybackController + Tests

**Files:**
- Create: `playback_controller.py`
- Create: `tests/test_playback_controller.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_playback_controller.py`:

```python
from unittest.mock import MagicMock, call
import pytest
from playback_controller import PlaybackController


def make_controller():
    engine = MagicMock()
    engine.is_music_playing.return_value = False
    engine.is_music_paused.return_value = False
    engine.is_jingle_playing.return_value = False
    ctrl = PlaybackController(engine)
    return ctrl, engine


class TestBackgroundMusic:
    def test_play_starts_first_track(self):
        ctrl, engine = make_controller()
        ctrl.set_background_playlist(["/a.mp3", "/b.mp3"])
        ctrl.play()
        engine.play_music.assert_called_once_with("/a.mp3")

    def test_play_does_nothing_with_empty_playlist(self):
        ctrl, engine = make_controller()
        ctrl.play()
        engine.play_music.assert_not_called()

    def test_stop(self):
        ctrl, engine = make_controller()
        ctrl.set_background_playlist(["/a.mp3"])
        ctrl.play()
        ctrl.stop()
        engine.stop_music.assert_called_once()

    def test_next_track_playlist_mode(self):
        ctrl, engine = make_controller()
        ctrl.set_background_playlist(["/a.mp3", "/b.mp3", "/c.mp3"])
        ctrl.play()
        ctrl.on_music_ended()
        assert engine.play_music.call_args_list[-1] == call("/b.mp3")
        ctrl.on_music_ended()
        assert engine.play_music.call_args_list[-1] == call("/c.mp3")
        ctrl.on_music_ended()
        assert engine.play_music.call_args_list[-1] == call("/a.mp3")

    def test_single_repeat_mode(self):
        ctrl, engine = make_controller()
        ctrl.set_background_playlist(["/a.mp3", "/b.mp3"])
        ctrl.set_repeat_mode("single")
        ctrl.play()
        ctrl.on_music_ended()
        assert engine.play_music.call_args_list[-1] == call("/a.mp3")

    def test_play_track_by_index(self):
        ctrl, engine = make_controller()
        ctrl.set_background_playlist(["/a.mp3", "/b.mp3", "/c.mp3"])
        ctrl.play_track(2)
        engine.play_music.assert_called_with("/c.mp3")

    def test_set_background_volume(self):
        ctrl, engine = make_controller()
        ctrl.set_background_volume(0.5)
        engine.set_music_volume.assert_called_with(0.5)


class TestJingleScenario:
    def test_jingle_without_music(self):
        ctrl, engine = make_controller()
        engine.is_music_playing.return_value = False
        ctrl.trigger_jingle("/j.mp3", 0.8)
        engine.play_jingle.assert_called_once_with("/j.mp3", 0.8)
        engine.fade_music_volume.assert_not_called()

    def test_jingle_with_music_triggers_fade_out(self):
        ctrl, engine = make_controller()
        ctrl.set_fade_out(2.0)
        engine.is_music_playing.return_value = True
        ctrl.trigger_jingle("/j.mp3", 0.8)
        engine.fade_music_volume.assert_called_once()
        args = engine.fade_music_volume.call_args
        assert args[0][0] == 0.0
        assert args[0][1] == 2.0
        engine.play_jingle.assert_called_once_with("/j.mp3", 0.8)

    def test_jingle_end_restores_music(self):
        ctrl, engine = make_controller()
        ctrl.set_fade_in(1.5)
        ctrl.set_background_volume(0.7)
        engine.is_music_playing.return_value = True

        ctrl.trigger_jingle("/j.mp3", 0.8)
        fade_callback = engine.fade_music_volume.call_args[1]["on_complete"]
        fade_callback()
        engine.pause_music.assert_called_once()

        ctrl.on_jingle_ended()
        engine.unpause_music.assert_called_once()
        last_fade = engine.fade_music_volume.call_args_list[-1]
        assert last_fade[0][0] == 0.7
        assert last_fade[0][1] == 1.5

    def test_jingle_queue(self):
        ctrl, engine = make_controller()
        engine.is_music_playing.return_value = True
        engine.is_jingle_playing.return_value = True

        ctrl.trigger_jingle("/j1.mp3", 0.8)
        ctrl.trigger_jingle("/j2.mp3", 0.5)

        assert engine.play_jingle.call_count == 1
        assert engine.play_jingle.call_args == call("/j1.mp3", 0.8)

        engine.is_jingle_playing.return_value = False
        ctrl.on_jingle_ended()
        assert engine.play_jingle.call_args == call("/j2.mp3", 0.5)
        engine.unpause_music.assert_not_called()

        ctrl.on_jingle_ended()
        engine.unpause_music.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_playback_controller.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'playback_controller'`

- [ ] **Step 3: Implement PlaybackController**

Create `playback_controller.py`:

```python
from PyQt6.QtCore import QObject, pyqtSignal


class PlaybackController(QObject):
    track_changed = pyqtSignal(int)
    jingle_started = pyqtSignal()
    jingle_queue_finished = pyqtSignal()

    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        self._playlist: list[str] = []
        self._current_index: int = 0
        self._repeat_mode: str = "playlist"
        self._bg_volume: float = 0.8
        self._fade_out: float = 2.0
        self._fade_in: float = 2.0
        self._is_playing: bool = False

        self._jingle_queue: list[tuple[str, float]] = []
        self._in_jingle_sequence: bool = False
        self._music_paused_for_jingle: bool = False
        self._had_music: bool = False

    def set_background_playlist(self, files: list[str]) -> None:
        self._playlist = list(files)
        self._current_index = 0

    def set_repeat_mode(self, mode: str) -> None:
        self._repeat_mode = mode

    def set_background_volume(self, volume: float) -> None:
        self._bg_volume = volume
        self._engine.set_music_volume(volume)

    def set_fade_out(self, sec: float) -> None:
        self._fade_out = sec

    def set_fade_in(self, sec: float) -> None:
        self._fade_in = sec

    def play(self) -> None:
        if not self._playlist:
            return
        self._is_playing = True
        self._engine.set_music_volume(self._bg_volume)
        self._engine.play_music(self._playlist[self._current_index])
        self.track_changed.emit(self._current_index)

    def stop(self) -> None:
        self._is_playing = False
        self._engine.stop_music()

    def play_track(self, index: int) -> None:
        if index < 0 or index >= len(self._playlist):
            return
        self._current_index = index
        self._is_playing = True
        self._engine.set_music_volume(self._bg_volume)
        self._engine.play_music(self._playlist[self._current_index])
        self.track_changed.emit(self._current_index)

    def on_music_ended(self) -> None:
        if not self._is_playing or not self._playlist:
            return
        if self._repeat_mode == "single":
            self._engine.play_music(self._playlist[self._current_index])
        else:
            self._current_index = (self._current_index + 1) % len(self._playlist)
            self._engine.play_music(self._playlist[self._current_index])
            self.track_changed.emit(self._current_index)

    def trigger_jingle(self, path: str, volume: float) -> None:
        if self._in_jingle_sequence:
            self._jingle_queue.append((path, volume))
            return

        self._in_jingle_sequence = True
        self._had_music = self._engine.is_music_playing()

        if self._had_music:
            self._engine.fade_music_volume(
                0.0, self._fade_out, on_complete=self._on_fade_out_done
            )

        self._engine.play_jingle(path, volume)
        self.jingle_started.emit()

    def on_jingle_ended(self) -> None:
        if self._jingle_queue:
            path, volume = self._jingle_queue.pop(0)
            self._engine.play_jingle(path, volume)
            return

        self._in_jingle_sequence = False

        if self._had_music:
            if self._music_paused_for_jingle:
                self._engine.unpause_music()
                self._music_paused_for_jingle = False
            self._engine.fade_music_volume(self._bg_volume, self._fade_in)

        self._had_music = False
        self.jingle_queue_finished.emit()

    def _on_fade_out_done(self) -> None:
        self._music_paused_for_jingle = True
        self._engine.pause_music()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_playback_controller.py -v`

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

Stage `playback_controller.py` and `tests/test_playback_controller.py`, commit with message `feat: PlaybackController with playlist logic, jingle scenario, and tests`.

---

### Task 5: TrackList Widget

**Files:**
- Create: `gui/track_list.py`

- [ ] **Step 1: Implement TrackList**

Create `gui/track_list.py`:

```python
import os
from PyQt6.QtWidgets import QListWidget, QAbstractItemView, QMenu
from PyQt6.QtCore import pyqtSignal, Qt


class TrackList(QListWidget):
    files_changed = pyqtSignal()
    track_activated = pyqtSignal(int)

    AUDIO_EXTENSIONS = (".mp3", ".wav")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_paths: list[str] = []

        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.itemDoubleClicked.connect(self._on_double_click)

    def get_files(self) -> list[str]:
        return list(self._file_paths)

    def set_files(self, paths: list[str]) -> None:
        self.clear()
        self._file_paths.clear()
        for p in paths:
            self._add_file(p)

    def _add_file(self, path: str) -> None:
        self._file_paths.append(path)
        self.addItem(os.path.basename(path))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(self.AUDIO_EXTENSIONS):
                    self._add_file(path)
            event.acceptProposedAction()
            self.files_changed.emit()
        else:
            source_row = self.currentRow()
            super().dropEvent(event)
            dest_row = self.currentRow()
            if source_row != dest_row and 0 <= source_row < len(self._file_paths):
                path = self._file_paths.pop(source_row)
                self._file_paths.insert(dest_row, path)
                self.files_changed.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._remove_selected()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            return
        menu = QMenu(self)
        remove_action = menu.addAction("Remove")
        action = menu.exec(event.globalPos())
        if action == remove_action:
            self._remove_selected()

    def _remove_selected(self) -> None:
        row = self.currentRow()
        if 0 <= row < len(self._file_paths):
            self._file_paths.pop(row)
            self.takeItem(row)
            self.files_changed.emit()

    def _on_double_click(self, item):
        row = self.row(item)
        self.track_activated.emit(row)
```

- [ ] **Step 2: Smoke test**

Run:
```python
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from gui.track_list import TrackList
w = TrackList()
w.set_files(['/fake/a.mp3', '/fake/b.wav'])
print(f'Files: {w.get_files()}')
print(f'Count: {w.count()}')
print('TrackList OK')
"
```

Expected: shows 2 files, prints `TrackList OK`

- [ ] **Step 3: Commit**

Stage `gui/track_list.py`, commit with message `feat: TrackList widget with drag-drop and reorder`.

---

### Task 6: JingleList Widget

**Files:**
- Create: `gui/jingle_list.py`

- [ ] **Step 1: Implement JingleList**

Create `gui/jingle_list.py`:

```python
import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QScrollArea,
    QMenu,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt


class JingleRow(QWidget):
    volume_changed = pyqtSignal(float)
    triggered = pyqtSignal()

    def __init__(self, name: str, volume: float = 1.0, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.label = QLabel(name)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(volume * 100))
        self.slider.setFixedWidth(100)
        self.slider.valueChanged.connect(
            lambda v: self.volume_changed.emit(v / 100.0)
        )
        layout.addWidget(self.slider)

    def get_volume(self) -> float:
        return self.slider.value() / 100.0

    def set_volume(self, volume: float) -> None:
        self.slider.setValue(int(volume * 100))

    def mouseDoubleClickEvent(self, event):
        self.triggered.emit()


class JingleList(QWidget):
    files_changed = pyqtSignal()
    jingle_triggered = pyqtSignal(int)
    volume_changed = pyqtSignal(int, float)

    AUDIO_EXTENSIONS = (".mp3", ".wav")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._file_paths: list[str] = []
        self._volumes: list[float] = []
        self._rows: list[JingleRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._container)

    def get_files(self) -> list[str]:
        return list(self._file_paths)

    def get_volumes(self) -> list[float]:
        return [r.get_volume() for r in self._rows]

    def set_jingles(self, jingles: list[tuple[str, float]]) -> None:
        self._clear_rows()
        for path, volume in jingles:
            self._add_jingle(path, volume)

    def _add_jingle(self, path: str, volume: float = 1.0) -> None:
        index = len(self._file_paths)
        self._file_paths.append(path)
        self._volumes.append(volume)

        row = JingleRow(os.path.basename(path), volume)
        row.triggered.connect(lambda idx=index: self.jingle_triggered.emit(idx))
        row.volume_changed.connect(lambda v, idx=index: self._on_volume(idx, v))
        row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        row.customContextMenuRequested.connect(
            lambda pos, idx=index: self._context_menu(idx, pos)
        )

        self._rows.append(row)
        self._layout.addWidget(row)

    def _on_volume(self, index: int, volume: float) -> None:
        if 0 <= index < len(self._volumes):
            self._volumes[index] = volume
            self.volume_changed.emit(index, volume)
            self.files_changed.emit()

    def _clear_rows(self) -> None:
        for row in self._rows:
            self._layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self._file_paths.clear()
        self._volumes.clear()

    def _remove_jingle(self, index: int) -> None:
        if 0 <= index < len(self._rows):
            path_vol = list(zip(self._file_paths, self._volumes))
            path_vol.pop(index)
            self._clear_rows()
            for path, volume in path_vol:
                self._add_jingle(path, volume)
            self.files_changed.emit()

    def _move_up(self, index: int) -> None:
        if index <= 0:
            return
        self._swap(index, index - 1)

    def _move_down(self, index: int) -> None:
        if index >= len(self._rows) - 1:
            return
        self._swap(index, index + 1)

    def _swap(self, i: int, j: int) -> None:
        self._file_paths[i], self._file_paths[j] = (
            self._file_paths[j],
            self._file_paths[i],
        )
        self._volumes[i], self._volumes[j] = self._volumes[j], self._volumes[i]
        saved = list(zip(self._file_paths, self._volumes))
        self._clear_rows()
        for path, volume in saved:
            self._add_jingle(path, volume)
        self.files_changed.emit()

    def _context_menu(self, index: int, pos) -> None:
        if index < 0 or index >= len(self._rows):
            return
        menu = QMenu(self)
        move_up = menu.addAction("Move Up")
        move_down = menu.addAction("Move Down")
        menu.addSeparator()
        remove = menu.addAction("Remove")

        action = menu.exec(self._rows[index].mapToGlobal(pos))
        if action == move_up:
            self._move_up(index)
        elif action == move_down:
            self._move_down(index)
        elif action == remove:
            self._remove_jingle(index)

    def highlight_jingle(self, index: int) -> None:
        for i, row in enumerate(self._rows):
            row.setStyleSheet("background-color: #3daee9;" if i == index else "")

    def clear_highlight(self) -> None:
        for row in self._rows:
            row.setStyleSheet("")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(self.AUDIO_EXTENSIONS):
                    self._add_jingle(path)
            event.acceptProposedAction()
            self.files_changed.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._rows:
                self._remove_jingle(len(self._rows) - 1)
        else:
            super().keyPressEvent(event)
```

- [ ] **Step 2: Smoke test**

Run:
```python
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from gui.jingle_list import JingleList
w = JingleList()
w.set_jingles([('/fake/j1.mp3', 0.7), ('/fake/j2.wav', 1.0)])
print(f'Files: {w.get_files()}')
print(f'Volumes: {w.get_volumes()}')
print('JingleList OK')
"
```

Expected: shows 2 files, volumes `[0.7, 1.0]`, prints `JingleList OK`

- [ ] **Step 3: Commit**

Stage `gui/jingle_list.py`, commit with message `feat: JingleList widget with per-item volume sliders and reorder`.

---

### Task 7: MainWindow

**Files:**
- Create: `gui/main_window.py`

- [ ] **Step 1: Implement MainWindow**

Create `gui/main_window.py`:

```python
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QSlider,
    QLabel,
    QSplitter,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from gui.track_list import TrackList
from gui.jingle_list import JingleList


class MainWindow(QMainWindow):
    play_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    repeat_mode_changed = pyqtSignal(str)
    background_volume_changed = pyqtSignal(float)
    fade_out_changed = pyqtSignal(float)
    fade_in_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Player")
        self.setMinimumSize(700, 500)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Top: two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # Left panel: background music
        left = QWidget()
        left_layout = QVBoxLayout(left)

        left_layout.addWidget(QLabel("Background Music"))

        btn_row = QHBoxLayout()
        self._play_btn = QPushButton("Play")
        self._stop_btn = QPushButton("Stop")
        self._play_btn.clicked.connect(self.play_clicked.emit)
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        btn_row.addWidget(self._play_btn)
        btn_row.addWidget(self._stop_btn)
        left_layout.addLayout(btn_row)

        self._repeat_group = QButtonGroup(self)
        self._radio_playlist = QRadioButton("Playlist loop")
        self._radio_single = QRadioButton("Single track loop")
        self._radio_playlist.setChecked(True)
        self._repeat_group.addButton(self._radio_playlist)
        self._repeat_group.addButton(self._radio_single)
        self._radio_playlist.toggled.connect(self._on_repeat_changed)
        left_layout.addWidget(self._radio_playlist)
        left_layout.addWidget(self._radio_single)

        self.track_list = TrackList()
        left_layout.addWidget(self.track_list, stretch=1)

        left_layout.addWidget(QLabel("Drag & drop audio files here"))

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Volume:"))
        self._bg_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._bg_volume_slider.setRange(0, 100)
        self._bg_volume_slider.setValue(80)
        self._bg_volume_slider.valueChanged.connect(
            lambda v: self.background_volume_changed.emit(v / 100.0)
        )
        vol_row.addWidget(self._bg_volume_slider)
        left_layout.addLayout(vol_row)

        splitter.addWidget(left)

        # Right panel: jingles
        right = QWidget()
        right_layout = QVBoxLayout(right)

        right_layout.addWidget(QLabel("Jingles"))

        self.jingle_list = JingleList()
        right_layout.addWidget(self.jingle_list, stretch=1)

        right_layout.addWidget(QLabel("Drag & drop audio files here"))

        splitter.addWidget(right)

        # Bottom: fade settings
        fade_box = QGroupBox("Crossfade Settings")
        fade_layout = QHBoxLayout(fade_box)

        fade_layout.addWidget(QLabel("Fade Out:"))
        self._fade_out_slider = QSlider(Qt.Orientation.Horizontal)
        self._fade_out_slider.setRange(0, 50)
        self._fade_out_slider.setValue(20)
        self._fade_out_label = QLabel("2.0s")
        self._fade_out_slider.valueChanged.connect(self._on_fade_out)
        fade_layout.addWidget(self._fade_out_slider)
        fade_layout.addWidget(self._fade_out_label)

        fade_layout.addSpacing(20)

        fade_layout.addWidget(QLabel("Fade In:"))
        self._fade_in_slider = QSlider(Qt.Orientation.Horizontal)
        self._fade_in_slider.setRange(0, 50)
        self._fade_in_slider.setValue(20)
        self._fade_in_label = QLabel("2.0s")
        self._fade_in_slider.valueChanged.connect(self._on_fade_in)
        fade_layout.addWidget(self._fade_in_slider)
        fade_layout.addWidget(self._fade_in_label)

        main_layout.addWidget(fade_box)

    def set_repeat_mode(self, mode: str) -> None:
        if mode == "single":
            self._radio_single.setChecked(True)
        else:
            self._radio_playlist.setChecked(True)

    def set_background_volume(self, volume: float) -> None:
        self._bg_volume_slider.setValue(int(volume * 100))

    def set_fade_out(self, sec: float) -> None:
        self._fade_out_slider.setValue(int(sec * 10))

    def set_fade_in(self, sec: float) -> None:
        self._fade_in_slider.setValue(int(sec * 10))

    def highlight_track(self, index: int) -> None:
        self.track_list.setCurrentRow(index)

    def _on_repeat_changed(self, checked: bool) -> None:
        if self._radio_playlist.isChecked():
            self.repeat_mode_changed.emit("playlist")
        else:
            self.repeat_mode_changed.emit("single")

    def _on_fade_out(self, value: int) -> None:
        sec = value / 10.0
        self._fade_out_label.setText(f"{sec:.1f}s")
        self.fade_out_changed.emit(sec)

    def _on_fade_in(self, value: int) -> None:
        sec = value / 10.0
        self._fade_in_label.setText(f"{sec:.1f}s")
        self.fade_in_changed.emit(sec)
```

- [ ] **Step 2: Smoke test — window opens**

Run:
```python
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from gui.main_window import MainWindow
w = MainWindow()
w.show()
print('MainWindow created OK')
"
```

Expected: `MainWindow created OK`

- [ ] **Step 3: Commit**

Stage `gui/main_window.py`, commit with message `feat: MainWindow with two-panel layout and fade controls`.

---

### Task 8: Entry Point — Wire Everything Together

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Implement full main.py**

Replace `main.py` with:

```python
import sys
import os
from PyQt6.QtWidgets import QApplication

from audio_engine import AudioEngine
from playback_controller import PlaybackController
from state_manager import StateManager, PlayerState, JingleEntry
from gui.main_window import MainWindow


def get_state_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "player_state.json")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Music Player")

    state_mgr = StateManager(get_state_path())
    state = state_mgr.load()

    engine = AudioEngine()
    controller = PlaybackController(engine)
    window = MainWindow()

    # Restore state
    controller.set_background_playlist(state.background_files)
    controller.set_background_volume(state.background_volume)
    controller.set_repeat_mode(state.repeat_mode)
    controller.set_fade_out(state.fade_out)
    controller.set_fade_in(state.fade_in)

    window.track_list.set_files(state.background_files)
    window.set_background_volume(state.background_volume)
    window.set_repeat_mode(state.repeat_mode)
    window.set_fade_out(state.fade_out)
    window.set_fade_in(state.fade_in)
    window.jingle_list.set_jingles(
        [(j.path, j.volume) for j in state.jingles]
    )

    # Save helper
    def save_state():
        s = PlayerState(
            background_files=window.track_list.get_files(),
            background_volume=controller._bg_volume,
            repeat_mode=controller._repeat_mode,
            jingles=[
                JingleEntry(path=p, volume=v)
                for p, v in zip(
                    window.jingle_list.get_files(),
                    window.jingle_list.get_volumes(),
                )
            ],
            fade_out=controller._fade_out,
            fade_in=controller._fade_in,
        )
        state_mgr.save(s)

    # GUI -> Controller
    window.play_clicked.connect(controller.play)
    window.stop_clicked.connect(controller.stop)
    window.repeat_mode_changed.connect(controller.set_repeat_mode)
    window.background_volume_changed.connect(controller.set_background_volume)
    window.fade_out_changed.connect(controller.set_fade_out)
    window.fade_in_changed.connect(controller.set_fade_in)

    window.track_list.track_activated.connect(controller.play_track)
    window.track_list.files_changed.connect(
        lambda: (
            controller.set_background_playlist(window.track_list.get_files()),
            save_state(),
        )
    )

    def on_jingle_triggered(index: int):
        files = window.jingle_list.get_files()
        volumes = window.jingle_list.get_volumes()
        if 0 <= index < len(files):
            controller.trigger_jingle(files[index], volumes[index])

    window.jingle_list.jingle_triggered.connect(on_jingle_triggered)
    window.jingle_list.files_changed.connect(save_state)

    # Save on setting changes
    window.background_volume_changed.connect(lambda _: save_state())
    window.repeat_mode_changed.connect(lambda _: save_state())
    window.fade_out_changed.connect(lambda _: save_state())
    window.fade_in_changed.connect(lambda _: save_state())

    # Engine -> Controller
    engine.music_ended.connect(controller.on_music_ended)
    engine.jingle_ended.connect(controller.on_jingle_ended)

    # Controller -> GUI
    controller.track_changed.connect(window.highlight_track)
    controller.jingle_started.connect(
        lambda: window.jingle_list.highlight_jingle(0)
    )
    controller.jingle_queue_finished.connect(window.jingle_list.clear_highlight)

    window.show()
    exit_code = app.exec()
    engine.cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the app and verify it launches**

Run: `python main.py`

Expected: window opens with two panels, fade controls at bottom. Close the window to exit cleanly.

- [ ] **Step 3: Manual integration test**

Test checklist:
1. Drag an MP3/WAV into the left panel — appears in list
2. Click Play — background music starts
3. Switch repeat mode — continues playing
4. Drag a jingle into the right panel — appears with volume slider
5. Double-click jingle — background fades out, jingle plays, background fades back in
6. Adjust fade sliders — verify timing changes
7. Close and reopen — state is restored

- [ ] **Step 4: Commit**

Stage `main.py`, commit with message `feat: wire all components in main.py entry point`.

---

### Task 9: Build Script

**Files:**
- Create: `build.py`

- [ ] **Step 1: Create build script**

Create `build.py`:

```python
import PyInstaller.__main__
import sys
import os


def build():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    name = "MusicPlayer"

    args = [
        script,
        "--name=" + name,
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--hidden-import=pygame",
        "--hidden-import=PyQt6",
    ]

    if sys.platform == "darwin":
        args.append("--osx-bundle-identifier=com.musicplayer.app")

    PyInstaller.__main__.run(args)
    print("Build complete. Output in dist/" + name + "/")


if __name__ == "__main__":
    build()
```

- [ ] **Step 2: Test the build**

Run: `python build.py`

Expected: builds without errors. Output in `dist/MusicPlayer/`.

- [ ] **Step 3: Run the built app and verify it works identically to `python main.py`**

macOS: `open dist/MusicPlayer/MusicPlayer.app`
Windows: `dist\MusicPlayer\MusicPlayer.exe`
Linux: `./dist/MusicPlayer/MusicPlayer`

- [ ] **Step 4: Commit**

Stage `build.py`, commit with message `feat: PyInstaller build script for standalone app`.

---

### Summary

| Task | What | Tests |
|------|------|-------|
| 1 | Project setup | — |
| 2 | StateManager | 4 unit tests |
| 3 | AudioEngine | smoke test |
| 4 | PlaybackController | 8 unit tests |
| 5 | TrackList widget | smoke test |
| 6 | JingleList widget | smoke test |
| 7 | MainWindow | smoke test |
| 8 | Wire everything in main.py | manual integration test |
| 9 | Build script | build and run |
