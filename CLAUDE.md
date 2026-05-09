# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Run

```bash
python main.py
```

Only dependency is `customtkinter>=5.2.0` (see `requirements.txt`).

## Architecture

```
main.py              → Entry point, creates PomodoroApp and calls mainloop()
pomodoro_app.py      → All UI: main window (PomodoroApp), settings dialog (SettingsDialog)
timer_engine.py      → Pure timer logic: Mode enum, TimerState enum, TimerEngine class
settings.py          → JSON-backed Settings and TodayStats (daily pomodoro counter)
```

- **TimerEngine** (`timer_engine.py`) — Headless state machine. Modes cycle WORK → SHORT_BREAK/LONG_BREAK → WORK. `tick(elapsed)` advances the timer by wall-clock delta; returns `False` when finished. `progress` is `remaining / total_duration` (0..1). The engine auto-advances mode on finish; the app layer handles sound + animation.
- **PomodoroApp** (`pomodoro_app.py`) — customtkinter root window. Polls `engine.tick()` every 500ms via `after()`. Renders the ring arc from `engine.progress`. Keyboard shortcuts: Space (start/pause), R (reset), S (skip).
- **Settings** (`settings.py`) — Reads/writes `pomodoro_settings.json`. Defaults: work 25min, short break 5min, long break 15min, interval every 4 pomodoros.
- **TodayStats** (`settings.py`) — Reads/writes `pomodoro_today.json`. Auto-resets count when date changes. Incremented when a break finishes (i.e., a work session completed).

## Data files

- `pomodoro_settings.json` — user-configurable durations and `always_on_top`
- `pomodoro_today.json` — `{"date": "...", "count": N}` auto-managed by TodayStats
