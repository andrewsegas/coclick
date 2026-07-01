"""CoClick GUI: dashboard to run/watch the bot + a setup panel to map positions
and tune attack thresholds. Drives :class:`bot_engine.BotEngine`."""

import queue
import time
import collections
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import pyautogui

import square
from bot_engine import (
    BotEngine,
    carregar_ini,
    salvar_posicao,
    save_settings,
    ensure_config,
)

# Friendly label + config key for every position the setup panel can capture.
POSITION_FIELDS = [
    ("next", "Next-village button"),
    ("atacar", "Attack button"),
    ("procurar", "Search button"),
    ("exercitoatacar", "Select-troops button"),
    ("atack", "Attack drag START"),
    ("atack2", "Attack drag END"),
    ("termina", "End-attack button"),
    ("ok", "OK button"),
    ("voltar", "Back button"),
]

STAT_ROWS = [
    ("status", "Status"),
    ("runtime", "Runtime"),
    ("attacks", "Attacks"),
    ("villages_skipped", "Skipped"),
    ("stars", "Stars"),
    ("last_read", "Last read (G/E/D)"),
]

# Loot tiles: (stat key, emoji, title, accent color)
LOOT_TILES = [
    ("gold_looted", "💰", "Gold", "#C9A227"),
    ("elixir_looted", "💧", "Elixir", "#B23A9A"),
    ("dark_looted", "🖤", "Dark elixir", "#444444"),
]

# Log level -> colour. "debug" lines are hidden unless "Show details" is on.
LOG_COLORS = {
    "debug": "#9aa0a6",
    "info": "#202124",
    "action": "#1a73e8",
    "success": "#0f9d58",
    "warn": "#e37400",
}

MAX_LOG_LINES = 500


class App:
    def __init__(self):
        ensure_config()

        self.queue = queue.Queue()
        self.engine = BotEngine(self.queue)
        self._latest_stats = {}
        self._log_entries = collections.deque(maxlen=MAX_LOG_LINES)

        self.root = tk.Tk()
        self.root.title("CoClick — Clash of Clans Farm Bot")
        self.root.minsize(880, 620)

        self.show_debug = tk.BooleanVar(value=False)

        self._build_ui()
        self._load_settings_into_fields()
        self._refresh_position_labels()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(200, self._drain_queue)
        self.root.after(1000, self._tick_runtime)

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        container = ttk.Frame(self.root, padding=8)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=3, uniform="col")
        container.columnconfigure(1, weight=2, uniform="col")
        container.rowconfigure(0, weight=1)

        self._build_dashboard(container)
        self._build_setup(container)

    def _build_dashboard(self, parent):
        frame = ttk.LabelFrame(parent, text="Dashboard", padding=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(4, weight=1)

        # Start/Stop toggle
        self.toggle_btn = ttk.Button(frame, text="▶  Start", command=self._toggle)
        self.toggle_btn.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # --- Loot tiles (the headline numbers) ---
        loot = ttk.Frame(frame)
        loot.grid(row=1, column=0, sticky="ew")
        self.loot_total_vars = {}
        self.loot_rate_vars = {}
        for i, (key, emoji, title, color) in enumerate(LOOT_TILES):
            loot.columnconfigure(i, weight=1, uniform="loot")
            tile = tk.Frame(loot, bd=1, relief="solid", padx=8, pady=6,
                            highlightbackground="#e0e0e0")
            tile.grid(row=0, column=i, sticky="nsew", padx=3)
            tk.Label(tile, text=f"{emoji} {title}", fg=color,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            total = tk.StringVar(value="0")
            self.loot_total_vars[key] = total
            tk.Label(tile, textvariable=total, fg=color,
                     font=("Segoe UI", 18, "bold")).pack(anchor="w")
            rate = tk.StringVar(value="0 / h")
            self.loot_rate_vars[key] = rate
            tk.Label(tile, textvariable=rate, fg="#666",
                     font=("Segoe UI", 8)).pack(anchor="w")

        # --- Secondary stats grid ---
        stats = ttk.Frame(frame)
        stats.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for c in range(4):
            stats.columnconfigure(c, weight=1)
        self.stat_vars = {}
        for idx, (key, label) in enumerate(STAT_ROWS):
            r, c = divmod(idx, 3)
            cell = ttk.Frame(stats)
            cell.grid(row=r, column=c, sticky="w", padx=(0, 12), pady=1)
            ttk.Label(cell, text=label + ":", foreground="#666").pack(side="left")
            var = tk.StringVar(value="—")
            self.stat_vars[key] = var
            ttk.Label(cell, textvariable=var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4, 0))
        self.stat_vars["status"].set("Idle")

        # --- Log header + details toggle ---
        header = ttk.Frame(frame)
        header.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Activity log", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w")
        ttk.Checkbutton(header, text="Show details", variable=self.show_debug,
                        command=self._rerender_log).grid(row=0, column=1, sticky="e")
        ttk.Button(header, text="Clear", width=6, command=self._clear_log).grid(
            row=0, column=2, sticky="e", padx=(6, 0))

        # --- Log ---
        self.log = ScrolledText(frame, height=12, state="disabled", wrap="word",
                                font=("Consolas", 9), background="#fbfbfb")
        self.log.grid(row=4, column=0, sticky="nsew", pady=(2, 0))
        self.log.tag_configure("time", foreground="#b0b0b0")
        for level, color in LOG_COLORS.items():
            self.log.tag_configure(level, foreground=color)

    def _build_setup(self, parent):
        frame = ttk.LabelFrame(parent, text="Setup", padding=8)
        frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        frame.columnconfigure(0, weight=1)

        # --- Positions ---
        pos = ttk.LabelFrame(frame, text="Screen positions", padding=6)
        pos.grid(row=0, column=0, sticky="ew")
        pos.columnconfigure(2, weight=1)

        self.capture_status = tk.StringVar(value="Hover the game, then click Capture.")
        ttk.Label(frame, textvariable=self.capture_status, foreground="#0a6").grid(
            row=1, column=0, sticky="w", pady=(4, 8))

        ttk.Label(pos, text="Reading area (OCR)").grid(row=0, column=0, sticky="w", pady=1)
        ttk.Button(pos, text="Capture", width=9,
                   command=self._capture_ocr_area).grid(row=0, column=1, padx=4, pady=1)
        self.pos_labels = {}
        ocr_val = tk.StringVar(value="")
        self.pos_labels["_ocr"] = ocr_val
        ttk.Label(pos, textvariable=ocr_val, foreground="#666").grid(row=0, column=2, sticky="w")

        for i, (key, friendly) in enumerate(POSITION_FIELDS, start=1):
            ttk.Label(pos, text=friendly).grid(row=i, column=0, sticky="w", pady=1)
            ttk.Button(pos, text="Capture", width=9,
                       command=lambda k=key, f=friendly: self._capture_position(k, f)
                       ).grid(row=i, column=1, padx=4, pady=1)
            val = tk.StringVar(value="")
            self.pos_labels[key] = val
            ttk.Label(pos, textvariable=val, foreground="#666").grid(row=i, column=2, sticky="w")

        # --- Attack settings ---
        atk = ttk.LabelFrame(frame, text="Attack settings", padding=6)
        atk.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        atk.columnconfigure(1, weight=1)

        self.gold_var = tk.StringVar()
        self.elixir_var = tk.StringVar()
        self.dark_var = tk.StringVar()
        self.star_var = tk.StringVar()
        self.minutes_var = tk.StringVar()

        vcmd = (self.root.register(self._validate_int), "%P")
        rows = [
            ("Min gold", self.gold_var),
            ("Min elixir", self.elixir_var),
            ("Min dark elixir", self.dark_var),
        ]
        for i, (label, var) in enumerate(rows):
            ttk.Label(atk, text=label).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Entry(atk, textvariable=var, validate="key", validatecommand=vcmd,
                      width=14).grid(row=i, column=1, sticky="w", pady=2)

        ttk.Label(atk, text="Strategy (star)").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Combobox(atk, textvariable=self.star_var, width=12, state="readonly",
                     values=("1", "2", "3")).grid(row=3, column=1, sticky="w", pady=2)
        ttk.Label(atk, text="1 = keep trophies · 2 = mixed · 3 = drop trophies",
                  foreground="#888").grid(row=4, column=0, columnspan=2, sticky="w")

        ttk.Label(atk, text="Auto-stop after (min)").grid(row=5, column=0, sticky="w", pady=(6, 2))
        ttk.Entry(atk, textvariable=self.minutes_var, width=14).grid(
            row=5, column=1, sticky="w", pady=(6, 2))
        ttk.Label(atk, text="(leave blank for unlimited)", foreground="#888").grid(
            row=6, column=0, columnspan=2, sticky="w")

        ttk.Button(frame, text="💾  Save settings", command=self._save_settings).grid(
            row=3, column=0, sticky="ew", pady=(10, 0))

    # -------------------------------------------------------------- helpers --
    @staticmethod
    def _validate_int(proposed):
        return proposed == "" or proposed.isdigit()

    @staticmethod
    def _fmt(n):
        """Compact human number: 1_234_567 -> '1.2M', 950_000 -> '950K'."""
        try:
            n = float(n)
        except (TypeError, ValueError):
            return "0"
        for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
            if abs(n) >= size:
                s = f"{n / size:.1f}".rstrip("0").rstrip(".")
                return f"{s}{unit}"
        return f"{int(n):,}"

    def _load_settings_into_fields(self):
        cfg = carregar_ini()
        atk = cfg.get("Ataque", {})
        self.gold_var.set(str(atk.get("gold", "")))
        self.elixir_var.set(str(atk.get("elixir", "")))
        self.dark_var.set(str(atk.get("blackelixir", "")))
        self.star_var.set(str(atk.get("star", "1")))
        tempo = cfg.get("Tempo", {})
        self.minutes_var.set(str(tempo.get("desligar_em_minutos", "")))

    def _refresh_position_labels(self):
        cfg = carregar_ini()
        pos = cfg.get("Posicoes", {})
        for key, var in self.pos_labels.items():
            if key == "_ocr":
                s1, s2 = pos.get("square1"), pos.get("square2")
                var.set(f"{s1} → {s2}" if s1 and s2 else "not set")
            else:
                v = pos.get(key)
                var.set(str(v) if v else "not set")

    # ------------------------------------------------------------- actions --
    def _toggle(self):
        if self.engine.is_running():
            self.toggle_btn.config(text="Stopping…", state="disabled")
            self.stat_vars["status"].set("Stopping…")
            self.engine.stop()
        else:
            self.toggle_btn.config(text="■  Stop")
            self.stat_vars["status"].set("Running")
            self.engine.start()

    def _capture_position(self, key, friendly):
        if self.engine.is_running():
            messagebox.showinfo("Busy", "Stop the bot before changing positions.")
            return
        self._countdown(3, key, friendly)

    def _countdown(self, n, key, friendly):
        if n > 0:
            self.capture_status.set(f"Move mouse to '{friendly}' — capturing in {n}…")
            self.root.after(1000, lambda: self._countdown(n - 1, key, friendly))
        else:
            pos = pyautogui.position()
            salvar_posicao(key, (pos[0], pos[1]))
            self.capture_status.set(f"Saved '{friendly}' at {pos[0]},{pos[1]}")
            self._refresh_position_labels()

    def _capture_ocr_area(self):
        if self.engine.is_running():
            messagebox.showinfo("Busy", "Stop the bot before changing positions.")
            return
        self.capture_status.set("Drag a rectangle over the resource numbers…")
        self.root.update_idletasks()
        area = square.Quadrado()
        area.start(master=self.root)
        salvar_posicao("square1", (area.start_x, area.start_y))
        salvar_posicao("square2", (area.end_x, area.end_y))
        self.capture_status.set("Saved OCR reading area.")
        self._refresh_position_labels()

    def _save_settings(self):
        ataque = {
            "gold": self.gold_var.get() or "0",
            "elixir": self.elixir_var.get() or "0",
            "blackelixir": self.dark_var.get() or "0",
            "star": self.star_var.get() or "1",
        }
        minutes = self.minutes_var.get().strip()
        tempo = {"desligar_em_minutos": minutes if minutes else ""}
        save_settings(ataque=ataque, tempo=tempo)
        self.capture_status.set("Settings saved.")
        messagebox.showinfo("Saved", "Attack settings saved to config.ini.")

    # --------------------------------------------------------- queue drain --
    def _drain_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    level, text = payload
                    self._add_log(level, text)
                elif kind == "status":
                    self.stat_vars["status"].set(payload)
                    if payload == "Stopped":
                        self._on_stopped()
                elif kind == "stats":
                    self._update_stats(payload)
                elif kind == "shutdown":
                    self._add_log("warn", "Auto-stop timer fired.")
        except queue.Empty:
            pass
        self.root.after(200, self._drain_queue)

    # ------------------------------------------------------------- logging --
    def _add_log(self, level, text):
        stamp = time.strftime("%H:%M:%S")
        self._log_entries.append((stamp, level, text))
        if level == "debug" and not self.show_debug.get():
            return
        self._write_log_line(stamp, level, text)

    def _write_log_line(self, stamp, level, text):
        self.log.config(state="normal")
        self.log.insert("end", f"{stamp}  ", ("time",))
        self.log.insert("end", text + "\n", (level,))
        self.log.see("end")
        self.log.config(state="disabled")

    def _rerender_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        for stamp, level, text in self._log_entries:
            if level == "debug" and not self.show_debug.get():
                continue
            self._write_log_line(stamp, level, text)

    def _clear_log(self):
        self._log_entries.clear()
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    # --------------------------------------------------------------- stats --
    def _update_stats(self, stats):
        self._latest_stats = stats
        self.stat_vars["attacks"].set(str(stats.get("attacks", 0)))
        self.stat_vars["villages_skipped"].set(str(stats.get("villages_skipped", 0)))
        self.stat_vars["stars"].set(str(stats.get("stars", 0)))
        money = self.engine.moneyWant
        self.stat_vars["last_read"].set(f"{money[0]:,} / {money[1]:,} / {money[2]:,}")
        self._refresh_loot()

    def _refresh_loot(self):
        stats = self._latest_stats
        start = stats.get("start_time")
        hours = 0.0
        if start:
            hours = max(time.time() - start, 1) / 3600.0
        for key, _emoji, _title, _color in LOOT_TILES:
            total = stats.get(key, 0)
            self.loot_total_vars[key].set(f"{total:,}")
            rate = int(total / hours) if hours else 0
            self.loot_rate_vars[key].set(f"{self._fmt(rate)} / h")

    def _tick_runtime(self):
        start = self._latest_stats.get("start_time")
        if start and self.engine.is_running():
            elapsed = int(time.time() - start)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self.stat_vars["runtime"].set(f"{h:02d}:{m:02d}:{s:02d}")
            self._refresh_loot()  # keep /h rates live even between attacks
        self.root.after(1000, self._tick_runtime)

    def _on_stopped(self):
        self.toggle_btn.config(text="▶  Start", state="normal")
        self.stat_vars["status"].set("Stopped")

    def _on_close(self):
        if self.engine.is_running():
            if not messagebox.askokcancel("Quit", "The bot is running. Stop and quit?"):
                return
            self.engine.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
