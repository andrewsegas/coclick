"""CoClick GUI: dashboard to run/watch the bot + a setup panel to map positions
and tune attack thresholds. Drives :class:`bot_engine.BotEngine`."""

import queue
import time
import threading
import collections
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import notifier
from wizard import SetupWizard, POINT, RECT
from bot_engine import (
    BotEngine,
    carregar_ini,
    salvar_posicao,
    save_settings,
    ensure_config,
)

# Every step the setup wizard captures, IN ORDER:
#   ("point", config_key, label)  or  ("rect", (tl_key, br_key), label)
WIZARD_STEPS = [
    ("point", "atacar", "Botão ATACAR (na vila)"),
    ("point", "procurar", "Botão PROCURAR vila"),
    ("point", "exercitoatacar", "Botão BATALHA (escolher tropas)"),
    ("rect", ("square1", "square2"), "Área do saque do INIMIGO (OCR)"),
    ("point", "next", "Botão PRÓXIMA vila (Next)"),
    ("point", "atack", "INÍCIO do arrasto do ataque"),
    ("point", "atack2", "FIM do arrasto do ataque"),
    ("point", "termina", "Botão RENDER"),
    ("point", "ok", "Botão OK (fim da batalha)"),
    ("point", "voltar", "Botão VOLTAR para casa"),
    ("rect", ("square3", "square4"), "Área dos MEUS recursos (OCR)"),
]

# Derived views of WIZARD_STEPS.
POSITION_FIELDS = [(s[1], s[2]) for s in WIZARD_STEPS if s[0] == "point"]
OCR_AREAS = [(s[1][0], s[1][1], s[2]) for s in WIZARD_STEPS if s[0] == "rect"]

FULL_MODE_ALL = "todos os limites atingidos"
FULL_MODE_ANY = "qualquer limite atingido"

STAT_ROWS = [
    ("status", "Status"),
    ("runtime", "Tempo"),
    ("attacks", "Ataques"),
    ("villages_skipped", "Puladas"),
    ("stars", "Estrelas"),
    ("last_read", "Última leitura (O/E/N)"),
]

# Loot tiles: (stat key, emoji, title, accent color)
LOOT_TILES = [
    ("gold_looted", "💰", "Ouro", "#C9A227"),
    ("elixir_looted", "💧", "Elixir", "#B23A9A"),
    ("dark_looted", "🖤", "Elixir negro", "#444444"),
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
        self.root.title("CoClick — Bot de farm para Clash of Clans")
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
        self.container = ttk.Frame(self.root, padding=8)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.container.columnconfigure(0, weight=3, uniform="col")
        self.container.columnconfigure(1, weight=2, uniform="col")
        self.container.rowconfigure(0, weight=1)

        self._build_dashboard(self.container)
        self._build_setup(self.container)
        self._setup_visible = True

    def _build_dashboard(self, parent):
        frame = ttk.LabelFrame(parent, text="Painel", padding=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(4, weight=1)

        # Start/Stop toggle + show/hide settings
        top = ttk.Frame(frame)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(0, weight=1)
        self.toggle_btn = ttk.Button(top, text="▶  Iniciar", command=self._toggle)
        self.toggle_btn.grid(row=0, column=0, sticky="ew")
        self.settings_btn = ttk.Button(top, text="⚙  Esconder", width=12,
                                       command=self._toggle_setup)
        self.settings_btn.grid(row=0, column=1, padx=(6, 0))

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
        self.stat_vars["status"].set("Aguardando")

        # --- Log header + details toggle ---
        header = ttk.Frame(frame)
        header.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Log de atividade", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w")
        ttk.Checkbutton(header, text="Mostrar detalhes", variable=self.show_debug,
                        command=self._rerender_log).grid(row=0, column=1, sticky="e")
        ttk.Button(header, text="Limpar", width=7, command=self._clear_log).grid(
            row=0, column=2, sticky="e", padx=(6, 0))

        # --- Log ---
        self.log = ScrolledText(frame, height=12, state="disabled", wrap="word",
                                font=("Consolas", 9), background="#fbfbfb")
        self.log.grid(row=4, column=0, sticky="nsew", pady=(2, 0))
        self.log.tag_configure("time", foreground="#b0b0b0")
        for level, color in LOG_COLORS.items():
            self.log.tag_configure(level, foreground=color)

    def _build_setup(self, parent):
        frame = ttk.LabelFrame(parent, text="Configuração", padding=8)
        frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        frame.columnconfigure(0, weight=1)
        self.setup_frame = frame

        # --- Positions ---
        pos = ttk.LabelFrame(frame, text="Posições na tela", padding=6)
        pos.grid(row=0, column=0, sticky="ew")
        pos.columnconfigure(0, weight=1)

        ttk.Button(pos, text="⚙  Configurar todas as posições (assistente)",
                   command=self._run_full_wizard).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.recapture_var = tk.StringVar()
        step_names = [s[2] for s in WIZARD_STEPS]
        ttk.Combobox(pos, textvariable=self.recapture_var, state="readonly",
                     values=step_names).grid(row=1, column=0, sticky="ew", pady=1)
        ttk.Button(pos, text="Recapturar", width=11,
                   command=self._recapture_selected).grid(
            row=1, column=1, padx=(4, 0), pady=1)

        vals = ttk.Frame(pos)
        vals.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        vals.columnconfigure(1, weight=1)
        self.pos_labels = {}
        value_rows = []
        area_i = 0
        for kind, key, label in WIZARD_STEPS:
            if kind == "point":
                value_rows.append((key, label))
            else:
                value_rows.append((f"_area{area_i}", label))
                area_i += 1
        for r, (key, friendly) in enumerate(value_rows):
            ttk.Label(vals, text=friendly, foreground="#666").grid(row=r, column=0, sticky="w")
            var = tk.StringVar(value="")
            self.pos_labels[key] = var
            ttk.Label(vals, textvariable=var, foreground="#666").grid(row=r, column=1, sticky="e")

        self.capture_status = tk.StringVar(
            value="Assistente: aponte o mouse para cada botão do jogo e aperte ESPAÇO.")
        ttk.Label(frame, textvariable=self.capture_status, foreground="#0a6").grid(
            row=1, column=0, sticky="w", pady=(4, 8))

        # --- Attack settings ---
        atk = ttk.LabelFrame(frame, text="Configurações de ataque", padding=6)
        atk.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        atk.columnconfigure(1, weight=1)

        self.gold_var = tk.StringVar()
        self.elixir_var = tk.StringVar()
        self.dark_var = tk.StringVar()
        self.star_var = tk.StringVar()
        self.minutes_var = tk.StringVar()

        vcmd = (self.root.register(self._validate_int), "%P")
        rows = [
            ("Ouro mínimo", self.gold_var),
            ("Elixir mínimo", self.elixir_var),
            ("Elixir negro mínimo", self.dark_var),
        ]
        for i, (label, var) in enumerate(rows):
            ttk.Label(atk, text=label).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Entry(atk, textvariable=var, validate="key", validatecommand=vcmd,
                      width=14).grid(row=i, column=1, sticky="w", pady=2)

        ttk.Label(atk, text="Estratégia (star)").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Combobox(atk, textvariable=self.star_var, width=12, state="readonly",
                     values=("1", "2", "3")).grid(row=3, column=1, sticky="w", pady=2)
        ttk.Label(atk, text="1 = mantém troféus · 2 = misto · 3 = perde troféus",
                  foreground="#888").grid(row=4, column=0, columnspan=2, sticky="w")

        ttk.Label(atk, text="Parar sozinho após (min)").grid(row=5, column=0, sticky="w", pady=(6, 2))
        ttk.Entry(atk, textvariable=self.minutes_var, width=14).grid(
            row=5, column=1, sticky="w", pady=(6, 2))
        ttk.Label(atk, text="(vazio = sem limite de tempo)", foreground="#888").grid(
            row=6, column=0, columnspan=2, sticky="w")

        # --- Auto-stop when storages are full ---
        full = ttk.LabelFrame(frame, text="Parada automática (armazéns cheios)", padding=6)
        full.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        full.columnconfigure(1, weight=1)

        self.full_stop_var = tk.BooleanVar(value=False)
        self.full_gold_var = tk.StringVar()
        self.full_elixir_var = tk.StringVar()
        self.full_mode_var = tk.StringVar(value=FULL_MODE_ALL)

        ttk.Checkbutton(full, text="Parar quando meus armazéns encherem",
                        variable=self.full_stop_var).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(full, text="Limite de ouro").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(full, textvariable=self.full_gold_var, validate="key",
                  validatecommand=vcmd, width=14).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(full, text="Limite de elixir").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(full, textvariable=self.full_elixir_var, validate="key",
                  validatecommand=vcmd, width=14).grid(row=2, column=1, sticky="w", pady=2)
        ttk.Label(full, text="Parar quando").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Combobox(full, textvariable=self.full_mode_var, state="readonly", width=22,
                     values=(FULL_MODE_ALL, FULL_MODE_ANY)).grid(
            row=3, column=1, sticky="w", pady=2)
        ttk.Label(full,
                  text="Lê os SEUS recursos na 'Área dos MEUS recursos (OCR)'.\n"
                       "Limite vazio/0 = ignora aquele recurso.",
                  foreground="#888").grid(row=4, column=0, columnspan=2, sticky="w")

        # --- Discord notifications ---
        notif = ttk.LabelFrame(frame, text="Notificações no Discord", padding=6)
        notif.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        notif.columnconfigure(1, weight=1)

        self.webhook_var = tk.StringVar()

        ttk.Label(notif, text="URL do webhook").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(notif, textvariable=self.webhook_var).grid(
            row=0, column=1, sticky="ew", pady=2)
        ttk.Button(notif, text="Testar", width=9, command=self._test_webhook).grid(
            row=0, column=2, sticky="e", padx=(4, 0), pady=2)
        ttk.Label(notif, text="Uma mensagem quando o bot parar (motivo + resumo da sessão).",
                  foreground="#888").grid(row=1, column=0, columnspan=3, sticky="w")

        ttk.Button(frame, text="💾  Salvar configurações", command=self._save_settings).grid(
            row=5, column=0, sticky="ew", pady=(10, 0))

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
        notif = cfg.get("Notificacoes", {})
        self.webhook_var.set(str(notif.get("discord_webhook", "")))
        parada = cfg.get("Parada", {})
        self.full_stop_var.set(bool(parada.get("parar_cheio", 0)))
        gold_lim = parada.get("cheio_ouro", 0)
        elixir_lim = parada.get("cheio_elixir", 0)
        self.full_gold_var.set(str(gold_lim) if gold_lim else "")
        self.full_elixir_var.set(str(elixir_lim) if elixir_lim else "")
        self.full_mode_var.set(
            FULL_MODE_ANY if str(parada.get("cheio_modo", "todos")) == "qualquer"
            else FULL_MODE_ALL)

    def _refresh_position_labels(self):
        cfg = carregar_ini()
        pos = cfg.get("Posicoes", {})
        for key, _friendly in POSITION_FIELDS:
            v = pos.get(key)
            self.pos_labels[key].set(str(v) if v else "não definido")
        for i, (k1, k2, _label) in enumerate(OCR_AREAS):
            a, b = pos.get(k1), pos.get(k2)
            self.pos_labels[f"_area{i}"].set(f"{a} → {b}" if a and b else "não definida")

    # ------------------------------------------------------------- actions --
    def _toggle_setup(self):
        if self._setup_visible:
            self.setup_frame.grid_remove()
            self.container.columnconfigure(1, weight=0, uniform="")
            self.settings_btn.config(text="⚙  Configurar")
        else:
            self.container.columnconfigure(1, weight=2, uniform="col")
            self.setup_frame.grid()
            self.settings_btn.config(text="⚙  Esconder")
        self._setup_visible = not self._setup_visible

    def _toggle(self):
        if self.engine.is_running():
            self.toggle_btn.config(text="Parando…", state="disabled")
            self.stat_vars["status"].set("Parando…")
            self.engine.stop()
        else:
            self.toggle_btn.config(text="■  Parar")
            self.stat_vars["status"].set("Rodando")
            self.engine.start()

    def _wizard_steps(self, only=None):
        """Build the wizard step list; ``only`` narrows it to one friendly label."""
        steps = []
        for kind, key, label in WIZARD_STEPS:
            if only is not None and only != label:
                continue
            if kind == "point":
                steps.append({
                    "kind": POINT, "label": label,
                    "save": lambda p, k=key: salvar_posicao(k, p),
                })
            else:
                k1, k2 = key
                steps.append({
                    "kind": RECT, "label": label,
                    "save": lambda r, a=k1, b=k2: (
                        salvar_posicao(a, (r[0], r[1])),
                        salvar_posicao(b, (r[2], r[3])),
                    ),
                })
        return steps

    def _run_full_wizard(self):
        self._run_wizard(self._wizard_steps())

    def _recapture_selected(self):
        selected = self.recapture_var.get()
        if not selected:
            messagebox.showinfo("Recapturar", "Escolha uma posição na lista primeiro.")
            return
        self._run_wizard(self._wizard_steps(only=selected))

    def _run_wizard(self, steps):
        if self.engine.is_running():
            messagebox.showinfo("Ocupado", "Pare o bot antes de mudar as posições.")
            return
        # Get the CoClick window out of the way so the game stays visible.
        self.root.iconify()
        self.root.update_idletasks()
        try:
            wiz = SetupWizard(self.root, steps).run()
        finally:
            self.root.deiconify()
        self._refresh_position_labels()
        if wiz.cancelled:
            self.capture_status.set(
                f"Assistente cancelado — {wiz.completed} passo(s) ficaram salvos.")
        else:
            self.capture_status.set(
                f"Pronto — {wiz.completed} de {len(steps)} passo(s) capturados.")

    def _save_settings(self):
        ataque = {
            "gold": self.gold_var.get() or "0",
            "elixir": self.elixir_var.get() or "0",
            "blackelixir": self.dark_var.get() or "0",
            "star": self.star_var.get() or "1",
        }
        minutes = self.minutes_var.get().strip()
        tempo = {"desligar_em_minutos": minutes if minutes else ""}
        notificacoes = {"discord_webhook": self.webhook_var.get().strip()}
        parada = {
            "parar_cheio": "1" if self.full_stop_var.get() else "0",
            "cheio_ouro": self.full_gold_var.get().strip() or "0",
            "cheio_elixir": self.full_elixir_var.get().strip() or "0",
            "cheio_modo": "qualquer" if self.full_mode_var.get() == FULL_MODE_ANY
                          else "todos",
        }
        save_settings(ataque=ataque, tempo=tempo, notificacoes=notificacoes,
                      parada=parada)
        self.capture_status.set("Configurações salvas.")
        messagebox.showinfo("Salvo", "Configurações salvas no config.ini.")

    def _test_webhook(self):
        url = self.webhook_var.get().strip()
        if not url:
            messagebox.showinfo(
                "Discord",
                "Cole a URL do seu webhook do Discord primeiro.\n"
                "(Canal → Editar → Integrações → Webhooks → Novo webhook → Copiar URL)",
            )
            return
        self.capture_status.set("Enviando notificação de teste…")

        def worker():
            error = notifier.send_test(url)
            self.root.after(0, lambda: self._test_webhook_done(error))

        threading.Thread(target=worker, daemon=True).start()

    def _test_webhook_done(self, error):
        if error is None:
            self.capture_status.set("Notificação de teste enviada — confira o Discord!")
            messagebox.showinfo("Discord", "Enviada! Confira o seu canal do Discord.")
        else:
            self.capture_status.set("A notificação de teste falhou.")
            messagebox.showerror("Discord", f"Não foi possível enviar a notificação:\n{error}")

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
                    if payload == "Parado":
                        self._on_stopped()
                elif kind == "stats":
                    self._update_stats(payload)
                elif kind == "shutdown":
                    self._add_log("warn", "O tempo limite foi atingido.")
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
        self.toggle_btn.config(text="▶  Iniciar", state="normal")
        self.stat_vars["status"].set("Parado")

    def _on_close(self):
        if self.engine.is_running():
            if not messagebox.askokcancel("Sair", "O bot está rodando. Parar e sair?"):
                return
            self.engine.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
