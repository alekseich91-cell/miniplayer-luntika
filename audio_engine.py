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

        # No pygame.display init — cannot use pygame.event subsystem.
        # Detect music end via get_busy() polling instead.

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
        if self._music_playing and not self._music_paused and not self._fade_timer.isActive():
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

    def set_jingle_volume(self, volume: float) -> None:
        self._jingle_channel.set_volume(max(0.0, min(1.0, volume)))

    def stop_jingle(self) -> None:
        self._jingle_channel.stop()
        self._jingle_playing = False

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
        # Detect music end via get_busy() — returns False when track finishes.
        # Also returns False when paused, so we guard with our own flags.
        if self._music_playing and not self._music_paused:
            if not pygame.mixer.music.get_busy():
                self._music_playing = False
                self.music_ended.emit()

        if self._jingle_playing and not self._jingle_channel.get_busy():
            self._jingle_playing = False
            self.jingle_ended.emit()
