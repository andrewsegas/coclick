"""CoClick bot engine.

Contains the farming logic extracted from the original ``coclick.py`` as a
controllable :class:`BotEngine` that runs its loop on a background thread and
reports status/log/stats to a GUI through a thread-safe queue.

The attack sequence, OCR crop/regex and every ``time.sleep`` / ``random.uniform``
timing are preserved verbatim from the original script -- this module only
changes *how the loop is controlled*, not what it does.
"""

import os
import re
import sys
import time
import random
import shutil
import threading
import configparser

import pytesseract
from PIL import ImageGrab
import pydirectinput
import pyautogui

import square


# --------------------------------------------------------------------------- #
# Path / resource helpers (frozen exe vs. running from source)
# --------------------------------------------------------------------------- #
def resource_path(rel):
    """Absolute path to a bundled resource, working both frozen and from source."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)


def config_path():
    """Path to the writable ``config.ini``, next to the exe when frozen."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(".")
    return os.path.join(base, "config.ini")


def _configure_tesseract():
    """Point pytesseract at the bundled Tesseract binary if present.

    When frozen, ``vendor/tesseract`` is shipped as data under ``tesseract/``.
    When running from source we fall back to the vendored folder if it exists,
    otherwise leave pytesseract's default (a system install) untouched.
    """
    bundled_exe = resource_path(os.path.join("tesseract", "tesseract.exe"))
    if os.path.exists(bundled_exe):
        pytesseract.pytesseract.tesseract_cmd = bundled_exe
        os.environ["TESSDATA_PREFIX"] = resource_path(
            os.path.join("tesseract", "tessdata")
        )


_configure_tesseract()


# --------------------------------------------------------------------------- #
# Config I/O (module-level so the GUI setup panel can call it directly)
# --------------------------------------------------------------------------- #
def salvar_posicao(nome, posicao, arquivo=None):
    """Save/update a single ``[Posicoes]`` coordinate in the ini file."""
    if arquivo is None:
        arquivo = config_path()
    config = configparser.ConfigParser()

    if os.path.exists(arquivo):
        config.read(arquivo)

    if "Posicoes" not in config:
        config["Posicoes"] = {}

    x, y = posicao
    config["Posicoes"][nome] = f"{x},{y}"

    with open(arquivo, "w") as configfile:
        config.write(configfile)


def save_settings(ataque=None, tempo=None, arquivo=None):
    """Write the ``[Ataque]`` / ``[Tempo]`` sections from the GUI setup panel.

    ``ataque`` / ``tempo`` are dicts of ``key -> value`` (values are stringified).
    Only the keys provided are written; existing keys are preserved/overwritten.
    """
    if arquivo is None:
        arquivo = config_path()
    config = configparser.ConfigParser()

    if os.path.exists(arquivo):
        config.read(arquivo)

    if ataque:
        if "Ataque" not in config:
            config["Ataque"] = {}
        for key, value in ataque.items():
            config["Ataque"][key] = str(value)

    if tempo is not None:
        if "Tempo" not in config:
            config["Tempo"] = {}
        for key, value in tempo.items():
            config["Tempo"][key] = str(value)

    with open(arquivo, "w") as configfile:
        config.write(configfile)


_DEFAULT_CONFIG = """[Posicoes]
next = 1752,695
atack = 1099,119
atack2 = 1491,412
termina = 130,727
ok = 1110,666
voltar = 954,924
atacar = 110,975
procurar = 277,771
square1 = 74,118
square2 = 252,256
exercitoatacar = 1606,925

[Ataque]
gold = 500000
elixir = 500000
blackelixir = 0
star = 1

[Tempo]
"""


def ensure_config():
    """Make sure a writable ``config.ini`` exists next to the exe.

    Seeds it from a bundled default (shipped as data) or, failing that, from a
    built-in template. Returns the resolved path.
    """
    path = config_path()
    if os.path.exists(path):
        return path
    default = resource_path("config.ini")
    if os.path.exists(default) and os.path.abspath(default) != os.path.abspath(path):
        shutil.copyfile(default, path)
    else:
        with open(path, "w") as f:
            f.write(_DEFAULT_CONFIG)
    return path


def carregar_ini(arquivo=None):
    """Load the ini file into a nested dict, converting ``x,y`` -> tuple and
    plain digits -> int (identical parsing to the original script)."""
    if arquivo is None:
        arquivo = config_path()
    config = configparser.ConfigParser()
    config.read(arquivo)

    dados = {}
    for secao in config.sections():
        dados[secao] = {}
        for chave, valor in config[secao].items():
            if "," in valor and all(v.strip().isdigit() for v in valor.split(",")):
                try:
                    x_str, y_str = valor.split(",")
                    dados[secao][chave] = (int(x_str), int(y_str))
                    continue
                except ValueError:
                    pass
            if valor.isdigit():
                dados[secao][chave] = int(valor)
            else:
                dados[secao][chave] = valor

    return dados


# --------------------------------------------------------------------------- #
# Bot engine
# --------------------------------------------------------------------------- #
class BotEngine:
    """Runs the farming loop on a daemon thread, controllable via start()/stop().

    Communicates with the GUI by putting tagged tuples on ``status_queue``:
        ("status", str)        -- high-level state (Idle/Running/Attacking/Stopped)
        ("log", (level, str))  -- a log line with a level: debug/info/action/success/warn
        ("stats", dict)        -- a snapshot of the stats counters
        ("shutdown", None)     -- the auto-shutdown timer fired
    """

    def __init__(self, status_queue):
        self.status_queue = status_queue
        self._stop_event = threading.Event()
        self._thread = None
        self._timer = None

        # migrated globals
        self.moneyWant = [0, 0, 0]
        self.vilacheck = 0
        self.tenta_ler = 0
        self.corrige_atack = 0
        self.posicoes = {}
        self.ataque_info = {}

        self.stats = {
            "attacks": 0,
            "villages_skipped": 0,
            "stars": 0,
            "gold_looted": 0,
            "elixir_looted": 0,
            "dark_looted": 0,
            "reads": 0,
            "start_time": None,
        }

    # ---- messaging helpers -------------------------------------------------
    def _emit_status(self, text):
        self.status_queue.put(("status", text))

    def _log(self, text, level="info"):
        self.status_queue.put(("log", (level, str(text))))

    def _emit_stats(self):
        self.status_queue.put(("stats", dict(self.stats)))

    # ---- lifecycle ---------------------------------------------------------
    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_running():
            return
        self._stop_event.clear()
        cfg = carregar_ini()
        self.posicoes = cfg.get("Posicoes", {})
        self.ataque_info = cfg.get("Ataque", {})
        self.stats["start_time"] = time.time()
        self._emit_stats()
        self._start_timer()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal the loop to stop. Cooperative: a running attack finishes first."""
        self._stop_event.set()
        self._cancel_timer()

    def _run(self):
        self._emit_status("Running")
        self._log("Bot started — searching for bases to farm.", "info")
        self.coloca_pra_atacar()
        while not self._stop_event.is_set():
            if self._stop_event.wait(1):
                break
            self._log("Scanning base…", "debug")
            cfg = carregar_ini()
            self.posicoes = cfg.get("Posicoes", {})
            self.ataque_info = cfg.get("Ataque", {})

            image = self.capture_screen()
            self.process_image(image)

            if self.corrige_atack > 5:
                self.coloca_pra_atacar()
                self.corrige_atack = 0

            if self.moneyWant[0] > 0 and self.moneyWant[1] > 0 and self.moneyWant[2] > 0:
                self.vilacheck += 1
                self.corrige_atack = 0
                self.check_attack(self.ataque_info)
            else:
                self._log("Couldn't read loot — adjusting view and retrying.", "warn")
                self.tenta_ler += 1
                if self.tenta_ler > 2:
                    self.vilacheck += 1
                    self.corrige_atack += 1
                    self.click_next()
                    self.tenta_ler = 0
                self.ajustar_click()

        self._log_session_summary()
        self._emit_status("Stopped")

    def _log_session_summary(self):
        s = self.stats
        start = s.get("start_time")
        runtime = self._format_hms(int(time.time() - start)) if start else "00:00:00"
        self._log(
            f"Session ended — {s['attacks']} attacks in {runtime} · "
            f"💰 {s['gold_looted']:,} gold · 💧 {s['elixir_looted']:,} elixir · "
            f"🖤 {s['dark_looted']:,} dark",
            "success",
        )

    @staticmethod
    def _format_hms(seconds):
        h, rem = divmod(max(seconds, 0), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ---- auto-shutdown timer ----------------------------------------------
    def _start_timer(self):
        config = configparser.ConfigParser()
        config.read(config_path())
        try:
            minutos = float(config.get("Tempo", "desligar_em_minutos"))
            segundos = minutos * 60
            self._timer = threading.Timer(segundos, self._on_timer)
            self._timer.start()
            self._log(f"Auto-stop scheduled in {minutos:g} minutes.", "info")
        except Exception:
            self._log("Running with no time limit.", "debug")

    def _cancel_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_timer(self):
        self._log("Auto-stop timer reached — stopping after the current base.", "info")
        self.stop()
        self.status_queue.put(("shutdown", None))

    # ---- screen / OCR ------------------------------------------------------
    def capture_screen(self):
        screenshot = ImageGrab.grab()
        return screenshot

    def process_image(self, image):
        cropped_image = image.crop(
            (
                self.posicoes.get("square1")[0],
                self.posicoes.get("square1")[1],
                self.posicoes.get("square2")[0],
                self.posicoes.get("square2")[1],
            )
        )
        text = pytesseract.image_to_string(cropped_image)
        lines = text.strip().split("\n")
        for i in range(3):
            if i < len(lines):
                num_str = re.sub(r"[^\d]", "", lines[i])
                if num_str:
                    self.moneyWant[i] = int(num_str)
                else:
                    self.moneyWant[i] = 0
            else:
                self.moneyWant[i] = 0
        self.stats["reads"] += 1
        self._emit_stats()
        if any(self.moneyWant):
            self._log(
                f"Read loot — 💰 {self.moneyWant[0]:,}  💧 {self.moneyWant[1]:,}  "
                f"🖤 {self.moneyWant[2]:,}",
                "debug",
            )

    # ---- attack sequence (verbatim timings) --------------------------------
    def startAttack(self):
        self.ajustar_click()
        self._emit_status("Attacking")
        self._log("Deploying troops…", "action")
        pydirectinput.press('1')
        pydirectinput.press('1')

        # cliica pra arrastar
        pyautogui.moveTo(self.posicoes.get("atack"), duration=0.3)
        pyautogui.click()

        pyautogui.mouseDown()
        time.sleep(4)
        pyautogui.moveTo(self.posicoes.get("atack2"), duration=1)  # Move o mouse para a posição final
        pyautogui.mouseUp()

        # Coloca todo o resto
        pyautogui.moveTo((self.posicoes.get("atack")[0]+self.posicoes.get("atack2")[0]) /2 , (self.posicoes.get("atack")[1]+self.posicoes.get("atack2")[1]) /2, duration = random.uniform(1,2) )  # Move o mouse para a posição final
        pyautogui.click()
        pyautogui.click()
        pydirectinput.press('z')
        pydirectinput.press('z')
        pyautogui.click()
        pydirectinput.press('q')
        pydirectinput.press('q')
        pyautogui.click()
        pydirectinput.press('w')
        pydirectinput.press('w')
        pyautogui.click()
        pydirectinput.press('e')
        pydirectinput.press('e')
        pyautogui.click()
        pydirectinput.press('r')
        pydirectinput.press('r')
        pyautogui.click()
        pydirectinput.press('a')
        pydirectinput.press('a')
        pyautogui.mouseDown()
        time.sleep(1)
        pyautogui.mouseUp()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pyautogui.click()
        pydirectinput.press('2')
        pyautogui.mouseDown()
        time.sleep(4)
        pyautogui.mouseUp()
        pydirectinput.press('3')
        pyautogui.mouseDown()
        time.sleep(3)
        pyautogui.mouseUp()

        time.sleep(random.uniform(5,8))
        pydirectinput.press('q')
        time.sleep(random.uniform(0,1))
        pydirectinput.press('w')
        time.sleep(random.uniform(0,2))
        pydirectinput.press('e')
        time.sleep(random.uniform(0,1))
        pydirectinput.press('r')

        if self.ataque_info['star'] == 1 or (self.ataque_info['star'] == 2 and random.uniform(1,10) > 5):
            # entra se star 1 ou se for 2 50% das vezes
            # espera o ataque acabar
            time.sleep(random.uniform(20,45))

        pyautogui.moveTo(self.posicoes.get("termina")[0] + round(random.uniform(-5,5)), self.posicoes.get("termina")[1] + round(random.uniform(-5,5)))
        pyautogui.click()

        time.sleep(random.uniform(2,3))
        pyautogui.moveTo(self.posicoes.get("ok")[0] + round(random.uniform(-5,5)), self.posicoes.get("ok")[1] + round(random.uniform(-5,5)) )
        pyautogui.click()

        time.sleep(random.uniform(2,3))
        pyautogui.moveTo(self.posicoes.get("voltar")[0] + round(random.uniform(-5,5)), self.posicoes.get("voltar")[1] + round(random.uniform(-5,5)))
        pyautogui.click()

        time.sleep(2)
        self.coloca_pra_atacar()

        self.ajustar_click()
        self._emit_status("Running")
        self._log(f"✔ Attack #{self.stats['attacks']} finished — searching next base.", "success")

    def coloca_pra_atacar(self):
        time.sleep(random.uniform(2,3))
        pyautogui.moveTo(self.posicoes.get("atacar")[0] + round(random.uniform(-5,5)), self.posicoes.get("atacar")[1] + round(random.uniform(-5,5)))
        pyautogui.click()

        time.sleep(random.uniform(2,3))
        pyautogui.moveTo(self.posicoes.get("procurar")[0] + round(random.uniform(-5,5)), self.posicoes.get("procurar")[1] + round(random.uniform(-5,5)))
        pyautogui.click()

        time.sleep(random.uniform(2,3))
        pyautogui.moveTo(self.posicoes.get("exercitoatacar")[0] + round(random.uniform(-5,5)), self.posicoes.get("exercitoatacar")[1] + round(random.uniform(-5,5)))
        pyautogui.click()

    def check_attack(self, ataque_info):
        # Verifica se o valor é maior
        if self.moneyWant[0] > ataque_info['gold'] and self.moneyWant[1] > ataque_info['elixir'] and self.moneyWant[2] > ataque_info['blackelixir']:
            self._log("Base is worth it — loot above your thresholds.", "info")
            self.vilacheck = 0
            self._record_attack()
            self.startAttack()

        elif self.vilacheck > 1 or ataque_info['star'] == 3:
            reason = "drop-trophy mode" if ataque_info['star'] == 3 else "skip limit reached"
            self._log(f"Attacking anyway ({reason}).", "info")
            self.vilacheck = 0
            self._record_attack()
            self.startAttack()
        else:
            self._log("Skipping base — loot below your thresholds.", "info")
            self.stats["villages_skipped"] += 1
            self._emit_stats()
            self.click_next()

    def _record_attack(self):
        self.stats["attacks"] += 1
        g, e, d = self.moneyWant[0], self.moneyWant[1], self.moneyWant[2]
        self.stats["gold_looted"] += g
        self.stats["elixir_looted"] += e
        self.stats["dark_looted"] += d
        star = self.ataque_info.get("star", 0)
        if isinstance(star, int):
            self.stats["stars"] += star
        self._emit_stats()
        self._log(
            f"▶ Attack #{self.stats['attacks']} — grabbing 💰 {g:,}  💧 {e:,}  🖤 {d:,}",
            "action",
        )

    def click_next(self):
        pyautogui.click(self.posicoes.get("next"))
        self._log("Next base…", "debug")
        time.sleep(5)
        self.ajustar_click()

    def ajustar_click(self):
        # cliica pra arrastar
        self._log("Adjusting map view.", "debug")
        pyautogui.moveTo(self.posicoes.get("square2"), duration=0.3)
        pyautogui.mouseDown()
        # clica pra arrastar
        pyautogui.moveTo(self.posicoes.get("next"), duration=0.3)  # Move o mouse para a posição do próximo botão
        pyautogui.mouseUp()


# --------------------------------------------------------------------------- #
# Manual smoke test (source only): drives one start/stop cycle.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import queue

    q = queue.Queue()
    engine = BotEngine(q)
    print("Config:", carregar_ini())
    print("Starting engine for 10s (Ctrl+C to abort)...")
    engine.start()
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                print(q.get(timeout=0.5))
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        print("Stopped.")
