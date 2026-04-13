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
            self._engine.unpause_music()
            self._music_paused_for_jingle = False
            self._engine.fade_music_volume(self._bg_volume, self._fade_in)

        self._had_music = False
        self.jingle_queue_finished.emit()

    def _on_fade_out_done(self) -> None:
        self._music_paused_for_jingle = True
        self._engine.pause_music()
