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

    def test_save_and_load_roundtrip(self, state_path, tmp_path):
        track1 = str(tmp_path / "track1.mp3")
        track2 = str(tmp_path / "track2.wav")
        jingle1 = str(tmp_path / "j1.mp3")
        jingle2 = str(tmp_path / "j2.wav")
        for p in (track1, track2, jingle1, jingle2):
            with open(p, "w") as f:
                f.write("fake")
        sm = StateManager(state_path)
        state = PlayerState(
            background_files=[track1, track2],
            background_volume=0.6,
            repeat_mode="single",
            jingles=[
                JingleEntry(path=jingle1, volume=0.7),
                JingleEntry(path=jingle2, volume=1.0),
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
        assert loaded.jingles[0].path == jingle1
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
