import sys
from PyQt6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Music Player")
    # Components will be wired here in Task 8
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
