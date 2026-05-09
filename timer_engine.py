from enum import Enum


class Mode(Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class TimerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


MODE_LABELS = {
    Mode.WORK: "工作中",
    Mode.SHORT_BREAK: "短休息",
    Mode.LONG_BREAK: "长休息",
}


class TimerEngine:
    def __init__(self, settings):
        self.settings = settings
        self.state = TimerState.IDLE
        self.mode = Mode.WORK
        self.remaining = settings.get("work_duration") * 60
        self.total_duration = self.remaining
        self.pomodoro_count = 0

    def start(self):
        if self.state in (TimerState.IDLE, TimerState.PAUSED):
            self.state = TimerState.RUNNING

    def pause(self):
        if self.state == TimerState.RUNNING:
            self.state = TimerState.PAUSED

    def reset(self):
        self.state = TimerState.IDLE
        self._set_duration_for_mode()

    def tick(self, elapsed_seconds):
        if self.state != TimerState.RUNNING:
            return False

        self.remaining = max(0, self.remaining - elapsed_seconds)

        if self.remaining <= 0:
            self._finish()
            return False
        return True

    @property
    def is_running(self):
        return self.state == TimerState.RUNNING

    @property
    def is_paused(self):
        return self.state == TimerState.PAUSED

    @property
    def is_idle(self):
        return self.state == TimerState.IDLE

    @property
    def progress(self):
        if self.total_duration == 0:
            return 0
        return self.remaining / self.total_duration

    def _finish(self):
        if self.mode == Mode.WORK:
            self.pomodoro_count += 1
            interval = self.settings.get("long_break_interval")
            if self.pomodoro_count % interval == 0:
                self.mode = Mode.LONG_BREAK
            else:
                self.mode = Mode.SHORT_BREAK
        else:
            self.mode = Mode.WORK

        self.state = TimerState.IDLE
        self._set_duration_for_mode()

    def _set_duration_for_mode(self):
        if self.mode == Mode.WORK:
            self.total_duration = self.settings.get("work_duration") * 60
        elif self.mode == Mode.SHORT_BREAK:
            self.total_duration = self.settings.get("short_break_duration") * 60
        else:
            self.total_duration = self.settings.get("long_break_duration") * 60
        self.remaining = self.total_duration

    def skip_to_next(self):
        self._finish()

    def update_durations(self):
        if self.state == TimerState.IDLE:
            self._set_duration_for_mode()
