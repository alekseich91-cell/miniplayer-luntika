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
