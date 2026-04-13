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

    def test_new_jingle_interrupts_current(self):
        ctrl, engine = make_controller()
        ctrl.set_fade_in(1.5)
        ctrl.set_background_volume(0.7)
        engine.is_music_playing.return_value = True

        ctrl.trigger_jingle("/j1.mp3", 0.8)
        assert engine.play_jingle.call_args == call("/j1.mp3", 0.8)

        # Second jingle interrupts the first
        ctrl.trigger_jingle("/j2.mp3", 0.5)
        engine.stop_jingle.assert_called_once()
        assert engine.play_jingle.call_args == call("/j2.mp3", 0.5)

        # When second jingle ends, music fades back in
        ctrl.on_jingle_ended()
        last_fade = engine.fade_music_volume.call_args_list[-1]
        assert last_fade[0][0] == 0.7
        assert last_fade[0][1] == 1.5

    def test_stop_jingle(self):
        ctrl, engine = make_controller()
        ctrl.set_fade_in(1.0)
        ctrl.set_background_volume(0.6)
        engine.is_music_playing.return_value = True

        ctrl.trigger_jingle("/j.mp3", 0.8)
        # Simulate fade out done
        fade_callback = engine.fade_music_volume.call_args[1]["on_complete"]
        fade_callback()

        ctrl.stop_jingle()
        engine.stop_jingle.assert_called_once()
        engine.unpause_music.assert_called_once()
        last_fade = engine.fade_music_volume.call_args_list[-1]
        assert last_fade[0][0] == 0.6
        assert last_fade[0][1] == 1.0
