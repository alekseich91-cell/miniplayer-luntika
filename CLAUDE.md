# Miniплеер Лунтика

Desktop music player для зацикливания фоновой музыки с джинглами через кроссфейд.

## Tech Stack

- **Python 3.13+**
- **PyQt6** — GUI
- **pygame.mixer** — аудио (mixer.music для фона, Channel(0) для джинглов)
- **PyInstaller** — сборка в standalone app
- **pytest** — тесты

## Architecture

Три слоя:
- `audio_engine.py` — обёртка pygame.mixer. Fade через QTimer (не pygame.fadeout — он останавливает вместо паузы). Polling через get_busy() (не pygame.event — требует display init).
- `playback_controller.py` — логика плейлиста, repeat modes, jingle-сценарий (fade out фона → джингл → fade in фона). Новый джингл прерывает текущий (без очереди).
- `gui/` — PyQt6 виджеты. MainWindow, TrackList (QListWidget + drag&drop), JingleList (custom rows с кнопкой ▶ и слайдером), JingleTabs (QTabWidget папок).

## Key Decisions

- `pygame.mixer.music` для фона (стриминг MP3), `pygame.mixer.Channel(0)` для джинглов (загрузка в память)
- Fade in/out через QTimer с шагом 30ms — ручное управление громкостью + pause/unpause для сохранения позиции
- Джинглы НЕ ставятся в очередь — новый прерывает текущий
- State persistence в JSON рядом с exe (`player_state.json`), атомарная запись через tempfile + os.replace

## Project Structure

```
main.py                  # Entry point, wiring
audio_engine.py          # pygame.mixer wrapper
playback_controller.py   # Playback logic
state_manager.py         # JSON state persistence
gui/
  main_window.py         # Main window layout
  track_list.py          # Background music list
  jingle_list.py         # Single jingle list (rows with ▶ + volume)
  jingle_tabs.py         # Tabbed jingle folders
tests/
  test_state_manager.py
  test_playback_controller.py
build.py                 # PyInstaller + codesign + DMG
```

## Commands

```bash
# Run
source venv/bin/activate
python main.py

# Test
pytest tests/ -v

# Build (macOS — creates .app + .dmg)
python build.py

# Windows build — via GitHub Actions (push to master triggers build)
```

## CI/CD

- GitHub Actions: `.github/workflows/build-windows.yml` — собирает .exe на push в master
- Releases: macOS DMG + Windows zip на GitHub Releases
