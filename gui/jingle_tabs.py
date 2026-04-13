import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QInputDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt
from gui.jingle_list import JingleList


class JingleTabs(QWidget):
    files_changed = pyqtSignal()
    jingle_triggered = pyqtSignal(str, float)  # path, volume
    volume_changed = pyqtSignal(int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab bar with add/remove buttons
        tab_bar = QHBoxLayout()
        self._add_tab_btn = QPushButton("+")
        self._add_tab_btn.setFixedSize(28, 28)
        self._add_tab_btn.setToolTip("Add folder")
        self._add_tab_btn.clicked.connect(self._on_add_tab)
        tab_bar.addWidget(self._add_tab_btn)

        self._rename_tab_btn = QPushButton("Rename")
        self._rename_tab_btn.setToolTip("Rename folder")
        self._rename_tab_btn.clicked.connect(self._on_rename_tab)
        tab_bar.addWidget(self._rename_tab_btn)

        self._remove_tab_btn = QPushButton("-")
        self._remove_tab_btn.setFixedSize(28, 28)
        self._remove_tab_btn.setToolTip("Remove folder")
        self._remove_tab_btn.clicked.connect(self._on_remove_tab)
        tab_bar.addWidget(self._remove_tab_btn)

        tab_bar.addStretch()
        layout.addLayout(tab_bar)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Create default tab
        self._ensure_default_tab()

    def _ensure_default_tab(self):
        if self._tabs.count() == 0:
            self._create_tab("General")

    def _create_tab(self, name: str) -> JingleList:
        jl = JingleList()
        jl.jingle_triggered.connect(lambda idx, jl=jl: self._on_jingle_triggered(jl, idx))
        jl.volume_changed.connect(self.volume_changed.emit)
        jl.files_changed.connect(self.files_changed.emit)
        self._tabs.addTab(jl, name)
        return jl

    def _on_jingle_triggered(self, jingle_list: JingleList, index: int):
        files = jingle_list.get_files()
        volumes = jingle_list.get_volumes()
        if 0 <= index < len(files):
            self.jingle_triggered.emit(files[index], volumes[index])

    def _on_add_tab(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            self._create_tab(name.strip())
            self.files_changed.emit()

    def _on_rename_tab(self):
        idx = self._tabs.currentIndex()
        if idx < 0:
            return
        old_name = self._tabs.tabText(idx)
        name, ok = QInputDialog.getText(self, "Rename Folder", "Folder name:", text=old_name)
        if ok and name.strip():
            self._tabs.setTabText(idx, name.strip())
            self.files_changed.emit()

    def _on_remove_tab(self):
        if self._tabs.count() <= 1:
            return
        idx = self._tabs.currentIndex()
        self._tabs.removeTab(idx)
        self.files_changed.emit()

    def clear_all(self):
        for i in range(self._tabs.count()):
            jl = self._tabs.widget(i)
            jl.set_jingles([])
        self.files_changed.emit()

    def get_all_tabs_data(self) -> list[dict]:
        result = []
        for i in range(self._tabs.count()):
            jl = self._tabs.widget(i)
            name = self._tabs.tabText(i)
            result.append({
                "name": name,
                "files": [
                    {"path": p, "volume": v}
                    for p, v in zip(jl.get_files(), jl.get_volumes())
                ],
            })
        return result

    def set_tabs_data(self, tabs_data: list[dict]) -> None:
        # Remove all existing tabs
        while self._tabs.count() > 0:
            self._tabs.removeTab(0)

        for tab in tabs_data:
            name = tab.get("name", "General")
            jl = self._create_tab(name)
            jingles = [
                (f["path"], f.get("volume", 1.0))
                for f in tab.get("files", [])
            ]
            jl.set_jingles(jingles)

        self._ensure_default_tab()

    def highlight_jingle(self, index: int) -> None:
        # Highlight on current tab
        jl = self._tabs.currentWidget()
        if jl:
            jl.highlight_jingle(index)

    def clear_highlight(self) -> None:
        for i in range(self._tabs.count()):
            jl = self._tabs.widget(i)
            jl.clear_highlight()
