import PyInstaller.__main__
import sys
import os


def build():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    name = "MusicPlayer"

    args = [
        script,
        "--name=" + name,
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--hidden-import=pygame",
        "--hidden-import=PyQt6",
    ]

    if sys.platform == "darwin":
        args.append("--osx-bundle-identifier=com.musicplayer.app")

    PyInstaller.__main__.run(args)
    print("Build complete. Output in dist/" + name + "/")


if __name__ == "__main__":
    build()
