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
