import time
import tkinter as tk
import customtkinter as ctk

from settings import Settings, TodayStats
from timer_engine import TimerEngine, Mode, TimerState, MODE_LABELS

# Muted, low-saturation palette
MODE_COLORS = {
    Mode.WORK: "#B8A090",
    Mode.SHORT_BREAK: "#90A890",
    Mode.LONG_BREAK: "#90A0B0",
}

GOLDEN = "#C8B090"
RING_BG = "#333333"
CANVAS_BG = "#2B2B2B"
TEXT_PRIMARY = "#E0DDD8"
TEXT_SECONDARY = "#777777"
TEXT_MUTED = "#555555"


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, settings, engine):
        super().__init__(parent)
        self.title("设置")
        self.geometry("360x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.settings = settings
        self.engine = engine
        self._vars = {}

        self._build_ui()

    def _build_ui(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=25)

        ctk.CTkLabel(frame, text="番茄钟设置", font=ctk.CTkFont(size=18, weight="normal")).pack(pady=(0, 20))

        self._add_spin_row(frame, "工作时长 (分钟)", "work_duration")
        self._add_spin_row(frame, "短休息时长 (分钟)", "short_break_duration")
        self._add_spin_row(frame, "长休息时长 (分钟)", "long_break_duration")
        self._add_spin_row(frame, "长休息间隔 (番茄数)", "long_break_interval")

        self._always_on_top_var = ctk.BooleanVar(value=self.settings.get("always_on_top"))
        cb = ctk.CTkCheckBox(frame, text="窗口置顶", variable=self._always_on_top_var,
                             border_color=TEXT_MUTED, fg_color=MODE_COLORS[Mode.WORK],
                             hover_color="#9A8070")
        cb.pack(pady=(15, 20), anchor="w")

        ctk.CTkButton(frame, text="保存", width=120, fg_color=MODE_COLORS[Mode.WORK],
                      hover_color="#9A8070", command=self._on_save).pack()

    def _add_spin_row(self, parent, label, key):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)

        ctk.CTkLabel(row, text=label, width=170, anchor="w",
                     text_color=TEXT_SECONDARY).pack(side="left")

        var = tk.StringVar(value=str(self.settings.get(key)))
        self._vars[key] = var

        entry = ctk.CTkEntry(row, width=70, textvariable=var, justify="center",
                             border_color="#444")
        entry.pack(side="right", padx=5)

    def _on_save(self):
        try:
            for key, var in self._vars.items():
                val = int(var.get())
                self.settings.set(key, val)
        except ValueError:
            return

        self.settings.set("always_on_top", self._always_on_top_var.get())

        if hasattr(self.master, "_apply_always_on_top"):
            self.master._apply_always_on_top()

        self.engine.update_durations()
        if hasattr(self.master, "_update_display"):
            self.master._update_display()

        self.destroy()


class PomodoroApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.settings = Settings()
        self.stats = TodayStats()
        self.engine = TimerEngine(self.settings)

        self.title("番茄钟")
        self.geometry("420x520")
        self.minsize(360, 460)

        self._tick_after_id = None
        self._last_tick_time = 0
        self._anim_after_ids = []

        self._build_ui()
        self._bind_keys()
        self._apply_always_on_top()
        self._update_display()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ─────────────────────────────────────────────

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=20)

        # Subtle settings button
        settings_btn = ctk.CTkButton(
            main, text="⚙", width=32, height=32,
            fg_color="transparent", hover_color="#3A3A3A",
            font=ctk.CTkFont(size=18),
            text_color=TEXT_MUTED,
            command=self._open_settings,
        )
        settings_btn.place(relx=1.0, y=0, anchor="ne")

        # Canvas ring
        self.canvas = tk.Canvas(main, width=320, height=320,
                                bg=CANVAS_BG, highlightthickness=0)
        self.canvas.pack(pady=(20, 20))
        self._draw_ring()

        # Subtle session indicator (replaces big emoji)
        self.session_label = ctk.CTkLabel(main, text="",
                                          font=ctk.CTkFont(size=12),
                                          text_color=TEXT_MUTED)
        self.session_label.pack(pady=(0, 8))

        # Button row — all outline style
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(pady=6)

        self.start_btn = ctk.CTkButton(
            btn_frame, text="开始", width=100, height=36,
            font=ctk.CTkFont(size=14),
            fg_color=MODE_COLORS[Mode.WORK], hover_color="#9A8070",
            border_width=1, border_color=MODE_COLORS[Mode.WORK],
            command=self._on_start_pause,
        )
        self.start_btn.pack(side="left", padx=6)

        self.reset_btn = ctk.CTkButton(
            btn_frame, text="重置", width=100, height=36,
            font=ctk.CTkFont(size=14),
            fg_color="transparent", hover_color="#333",
            border_width=1, border_color="#444",
            text_color=TEXT_SECONDARY,
            command=self._on_reset,
        )
        self.reset_btn.pack(side="left", padx=6)

        self.skip_btn = ctk.CTkButton(
            btn_frame, text="跳过", width=100, height=36,
            font=ctk.CTkFont(size=14),
            fg_color="transparent", hover_color="#333",
            border_width=1, border_color="#444",
            text_color=TEXT_SECONDARY,
            command=self._on_skip,
        )
        self.skip_btn.pack(side="left", padx=6)

        # Keyboard hint — very subtle
        ctk.CTkLabel(main, text="Space  ·  R  ·  S",
                     font=ctk.CTkFont(size=10), text_color="#444").pack(pady=(18, 0))

    def _draw_ring(self):
        cx, cy = 160, 160
        r = 120
        width = 14

        self.ring_width = width

        # Background track
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-359.9,
            outline=RING_BG, width=width,
            style="arc", tags="bg_ring",
        )

        # Progress arc
        self.progress_arc = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-359.9,
            outline=MODE_COLORS[Mode.WORK], width=width,
            style="arc", tags="progress_ring",
        )

        # Timer digits
        self.timer_text = self.canvas.create_text(
            cx, cy - 12, text="25:00",
            font=("Helvetica", 48, "normal"),
            fill=TEXT_PRIMARY, tags="timer_text",
        )

        # Mode label
        self.mode_text = self.canvas.create_text(
            cx, cy + 40, text="工作中",
            font=("Helvetica", 13, "normal"),
            fill=TEXT_SECONDARY, tags="mode_text",
        )

    # ── Keyboard bindings ────────────────────────────────────────────

    def _bind_keys(self):
        self.bind("<space>", lambda e: self._on_start_pause())
        self.bind("<Key-r>", lambda e: self._on_reset())
        self.bind("<Key-s>", lambda e: self._on_skip())

    # ── Display update ───────────────────────────────────────────────

    def _update_display(self):
        remaining = self.engine.remaining
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)

        self.canvas.itemconfigure(self.timer_text, text=f"{minutes:02d}:{seconds:02d}")

        subtitle = MODE_LABELS[self.engine.mode]
        if self.engine.is_paused:
            subtitle += " · 已暂停"
        self.canvas.itemconfigure(self.mode_text, text=subtitle)

        color = MODE_COLORS[self.engine.mode]
        extent = -360 * max(0, min(1, self.engine.progress))
        self.canvas.itemconfigure(self.progress_arc, extent=extent, outline=color)

        # Start button adapts to state
        if self.engine.is_running:
            self.start_btn.configure(text="暂停", fg_color=color, hover_color=self._dim(color),
                                     border_color=color)
        elif self.engine.is_paused:
            self.start_btn.configure(text="继续", fg_color=color, hover_color=self._dim(color),
                                     border_color=color)
        else:
            self.start_btn.configure(text="开始", fg_color=color, hover_color=self._dim(color),
                                     border_color=color)

        # Subtle session progress
        if self.engine.pomodoro_count > 0:
            self.session_label.configure(text=f"本次完成 {self.engine.pomodoro_count} 个番茄  ·  今日 {self.stats.get_today_count()} 个")
        else:
            today = self.stats.get_today_count()
            if today > 0:
                self.session_label.configure(text=f"今日完成 {today} 个番茄")
            else:
                self.session_label.configure(text="")

    @staticmethod
    def _dim(hex_color):
        """Darken a hex color by ~15% for hover states."""
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r, g, b = max(0, r - 25), max(0, g - 25), max(0, b - 25)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── Timer controls ────────────────────────────────────────────────

    def _on_start_pause(self):
        if self.engine.is_running:
            self.engine.pause()
            self._stop_ticking()
        else:
            self.engine.start()
            self._start_ticking()
        self._update_display()

    def _on_reset(self):
        self._cancel_animations()
        self._stop_ticking()
        self.engine.reset()
        self._reset_ring_style()
        self._update_display()

    def _on_skip(self):
        self._cancel_animations()
        self._stop_ticking()
        self.engine.skip_to_next()
        self._reset_ring_style()
        self._update_display()
        self._play_sound()

    def _start_ticking(self):
        self._last_tick_time = time.time()
        self._do_tick()

    def _do_tick(self):
        now = time.time()
        elapsed = min(now - self._last_tick_time, 1.0)
        self._last_tick_time = now

        still_running = self.engine.tick(elapsed)
        self._update_display()

        if still_running:
            self._tick_after_id = self.after(500, self._do_tick)
        else:
            if self.engine.is_idle:
                self._on_timer_finished()

    def _stop_ticking(self):
        if self._tick_after_id is not None:
            self.after_cancel(self._tick_after_id)
            self._tick_after_id = None

    # ── Completion ────────────────────────────────────────────────────

    def _on_timer_finished(self):
        self._play_sound()
        self._animate_completion()
        if self.engine.mode in (Mode.SHORT_BREAK, Mode.LONG_BREAK):
            self.stats.increment()
        self._update_display()

    def _play_sound(self):
        try:
            import winsound
            winsound.Beep(587, 120)
            winsound.Beep(784, 120)
            winsound.Beep(988, 200)
        except Exception:
            pass

    def _animate_completion(self):
        """Gentle ring pulse: expand → golden → contract → mode color."""
        step_delay = 80
        base_w = self.ring_width
        peak_w = base_w + 8

        def step1():
            self.canvas.itemconfigure(self.progress_arc, outline=GOLDEN, width=base_w + 4)

        def step2():
            self.canvas.itemconfigure(self.progress_arc, width=peak_w)

        def step3():
            self.canvas.itemconfigure(self.progress_arc, width=base_w + 4)

        def step4():
            self.canvas.itemconfigure(self.progress_arc, width=base_w)
            color = MODE_COLORS[self.engine.mode]
            self.canvas.itemconfigure(self.progress_arc, outline=color)
            self._update_display()

        self._anim_after_ids = [
            self.after(0, step1),
            self.after(step_delay, step2),
            self.after(step_delay * 2, step3),
            self.after(step_delay * 3, step4),
        ]

    def _reset_ring_style(self):
        self.canvas.itemconfigure(self.progress_arc, width=self.ring_width)
        self.canvas.itemconfigure(self.progress_arc, outline=MODE_COLORS[self.engine.mode])

    def _cancel_animations(self):
        for aid in self._anim_after_ids:
            self.after_cancel(aid)
        self._anim_after_ids.clear()

    # ── Window management ─────────────────────────────────────────────

    def _open_settings(self):
        SettingsDialog(self, self.settings, self.engine)

    def _apply_always_on_top(self):
        self.attributes("-topmost", self.settings.get("always_on_top"))

    def _on_close(self):
        self._cancel_animations()
        self._stop_ticking()
        self.destroy()
