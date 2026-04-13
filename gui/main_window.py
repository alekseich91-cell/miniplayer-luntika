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
