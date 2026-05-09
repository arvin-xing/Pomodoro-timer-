import json
import os
from datetime import date

DEFAULT_SETTINGS = {
    "work_duration": 25,
    "short_break_duration": 5,
    "long_break_duration": 15,
    "long_break_interval": 4,
    "always_on_top": False,
}

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_settings.json")
TODAY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_today.json")


class Settings:
    def __init__(self):
        self.data = self._load(SETTINGS_FILE, DEFAULT_SETTINGS)

    def _load(self, path, defaults):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {**defaults, **data}
            except (json.JSONDecodeError, IOError):
                return defaults.copy()
        return defaults.copy()

    def save(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get(self, key):
        return self.data.get(key, DEFAULT_SETTINGS[key])

    def set(self, key, value):
        self.data[key] = value
        self.save()


class TodayStats:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(TODAY_FILE):
            try:
                with open(TODAY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"date": "", "count": 0}

    def _save(self):
        with open(TODAY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get_today_count(self):
        today = date.today().isoformat()
        if self.data["date"] != today:
            self.data = {"date": today, "count": 0}
            self._save()
        return self.data["count"]

    def increment(self):
        today = date.today().isoformat()
        if self.data["date"] != today:
            self.data = {"date": today, "count": 0}
        self.data["count"] += 1
        self._save()
