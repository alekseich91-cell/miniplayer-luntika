import PyInstaller.__main__
import subprocess
import sys
import os


def build():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    base = os.path.dirname(os.path.abspath(__file__))
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
        args.append("--osx-bundle-identifier=com.luntik.miniplayer")
        args.append("--codesign-identity=-")  # ad-hoc signing

    PyInstaller.__main__.run(args)

    app_path = os.path.join(base, "dist", name + ".app")
    if sys.platform == "darwin" and os.path.exists(app_path):
        # Deep ad-hoc sign all binaries inside the bundle
        print("Signing app bundle...")
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", app_path],
            check=True,
        )
        print("Signed successfully.")

        # Create DMG for convenient distribution
        dmg_path = os.path.join(base, "dist", name + ".dmg")
        if os.path.exists(dmg_path):
            os.remove(dmg_path)
        print("Creating DMG...")
        subprocess.run(
            ["hdiutil", "create", "-volname", name,
             "-srcfolder", app_path,
             "-ov", "-format", "UDZO", dmg_path],
            check=True,
        )
        print("DMG created: dist/" + name + ".dmg")

    print("Build complete.")


if __name__ == "__main__":
    build()
