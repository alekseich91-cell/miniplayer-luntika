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
