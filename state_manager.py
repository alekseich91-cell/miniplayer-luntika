import json
import os
import tempfile
from dataclasses import dataclass, field


@dataclass
class JingleEntry:
    path: str
    volume: float = 1.0


@dataclass
class JingleTab:
    name: str
    jingles: list[JingleEntry] = field(default_factory=list)


@dataclass
class PlayerState:
    background_files: list[str] = field(default_factory=list)
    background_volume: float = 0.8
    repeat_mode: str = "playlist"
    jingles: list[JingleEntry] = field(default_factory=list)
    jingle_tabs: list[JingleTab] = field(default_factory=list)
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
                JingleEntry(path=j.get("path", ""), volume=float(j.get("volume", 1.0)))
                for j in jingles_data
                if os.path.exists(j.get("path", ""))
            ]

            tabs_data = data.get("jingle_tabs", [])
            jingle_tabs = []
            for tab in tabs_data:
                entries = [
                    JingleEntry(path=j.get("path", ""), volume=float(j.get("volume", 1.0)))
                    for j in tab.get("files", [])
                    if os.path.exists(j.get("path", ""))
                ]
                jingle_tabs.append(JingleTab(name=tab.get("name", "General"), jingles=entries))

            fade_out = float(data.get("fade_out", 2.0))
            fade_in = float(data.get("fade_in", 2.0))

            return PlayerState(
                background_files=bg_files,
                background_volume=bg_volume,
                repeat_mode=repeat_mode,
                jingles=jingles,
                jingle_tabs=jingle_tabs,
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
            "jingle_tabs": [
                {
                    "name": tab.name,
                    "files": [
                        {"path": j.path, "volume": j.volume} for j in tab.jingles
                    ],
                }
                for tab in state.jingle_tabs
            ],
            "fade_out": state.fade_out,
            "fade_in": state.fade_in,
        }
        try:
            dir_ = os.path.dirname(self._path) or "."
            fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp_path, self._path)
            except BaseException:
                os.unlink(tmp_path)
                raise
        except OSError:
            pass
