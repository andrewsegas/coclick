"""Guided setup wizard: hover the game and press SPACE to capture.

The wizard does NOT cover the screen — the game stays fully interactive, so
buttons that only appear after navigating menus can be reached normally. A
small always-on-top banner shows the current instruction, and the keys are
read globally through the Win32 API (GetAsyncKeyState), so they work even
while the game window has focus.

Controls:
  SPACE       capture the mouse position (OCR areas take two presses:
              top-left corner, then bottom-right corner)
  right-click skip the step (keeps the saved value)
  Esc         cancel the remaining steps

Every captured step is saved immediately by the caller-provided ``save``
callback, so progress survives a cancel.
"""

import ctypes
import tkinter as tk

POINT = "point"
RECT = "rect"

_VK_RBUTTON = 0x02
_VK_ESCAPE = 0x1B
_VK_SPACE = 0x20
_POLL_MS = 40
_MIN_AREA_PX = 5


class _CursorPos(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def _cursor_pos():
    pt = _CursorPos()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _key_down(vk):
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


class SetupWizard:
    """Run with ``SetupWizard(master, steps).run()``.

    ``steps`` is a list of dicts::

        {"kind": POINT, "label": "Attack button", "save": lambda pos: ...}
        {"kind": RECT,  "label": "Loot area",     "save": lambda rect: ...}

    ``save`` receives ``(x, y)`` for POINT and ``(x1, y1, x2, y2)`` for RECT,
    all in screen coordinates. After ``run()``, ``completed`` holds how many
    steps were captured and ``cancelled`` whether Esc was pressed.
    """

    def __init__(self, master, steps):
        self.master = master
        self.steps = steps
        self.index = 0
        self.completed = 0
        self.cancelled = False
        self._first_corner = None
        self._banner_at_top = True
        # Start every key as "down" so a key already held when the wizard
        # opens doesn't fire on the first poll.
        self._prev_down = {_VK_SPACE: True, _VK_RBUTTON: True, _VK_ESCAPE: True}

    # ------------------------------------------------------------------ run --
    def run(self):
        self.banner = tk.Toplevel(self.master)
        self.banner.overrideredirect(True)
        self.banner.attributes("-topmost", True)
        self.banner.configure(bg="#202124")
        # Big label: WHICH button to hover. Small label: the controls.
        self.banner_label = tk.Label(
            self.banner, font=("Segoe UI", 17, "bold"), justify="center",
            bg="#202124", fg="white", padx=20, pady=(10),
        )
        self.banner_label.pack()
        self.hint_label = tk.Label(
            self.banner, font=("Segoe UI", 9), justify="center",
            bg="#202124", fg="#9aa0a6", padx=20, pady=(0),
        )
        self.hint_label.pack(pady=(0, 8))
        # If the banner covers something you need to see, click it to flip it
        # to the other edge of the screen.
        for widget in (self.banner_label, self.hint_label):
            widget.bind("<Button-1>", self._flip_banner)

        self._show_step()
        self._poll()
        self.master.wait_window(self.banner)
        return self

    # ------------------------------------------------------------ rendering --
    def _show_step(self):
        step = self.steps[self.index]
        if step["kind"] == POINT:
            main = f"{step['label']}\nmouse em cima  →  ESPAÇO"
        elif self._first_corner is None:
            main = f"{step['label']}\ncanto SUPERIOR ESQUERDO  →  ESPAÇO"
        else:
            main = f"{step['label']}\nagora o canto INFERIOR DIREITO  →  ESPAÇO"
        self.banner_label.config(text=main)
        self.hint_label.config(
            text=(
                f"passo {self.index + 1} de {len(self.steps)}  ·  "
                "botão direito = pular  ·  Esc = cancelar  ·  clique aqui = mover este aviso"
            )
        )
        self._place_banner()

    def _place_banner(self):
        self.banner.update_idletasks()
        w = self.banner.winfo_reqwidth()
        h = self.banner.winfo_reqheight()
        sw = self.banner.winfo_screenwidth()
        sh = self.banner.winfo_screenheight()
        y = 16 if self._banner_at_top else sh - h - 16
        self.banner.geometry(f"+{(sw - w) // 2}+{y}")

    def _flip_banner(self, _event):
        self._banner_at_top = not self._banner_at_top
        self._place_banner()

    # -------------------------------------------------------- global keys ---
    def _poll(self):
        if not self.banner.winfo_exists():
            return
        for vk, handler in (
            (_VK_SPACE, self._on_capture),
            (_VK_RBUTTON, self._on_skip),
            (_VK_ESCAPE, self._on_cancel),
        ):
            down = _key_down(vk)
            fired = down and not self._prev_down[vk]
            self._prev_down[vk] = down
            if fired:
                handler()
                if not self.banner.winfo_exists():
                    return
        self.banner.after(_POLL_MS, self._poll)

    def _on_capture(self):
        step = self.steps[self.index]
        x, y = _cursor_pos()
        if step["kind"] == POINT:
            step["save"]((x, y))
        else:
            if self._first_corner is None:
                self._first_corner = (x, y)
                self._show_step()
                return
            x1, y1 = self._first_corner
            x2, y2 = x, y
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            if x2 - x1 < _MIN_AREA_PX or y2 - y1 < _MIN_AREA_PX:
                # Both corners on (almost) the same spot: restart this area.
                self._first_corner = None
                self._show_step()
                return
            step["save"]((x1, y1, x2, y2))
            self._first_corner = None
        self.completed += 1
        self._advance()

    def _on_skip(self):
        self._first_corner = None
        self._advance()

    def _on_cancel(self):
        self.cancelled = True
        self.banner.destroy()

    def _advance(self):
        self.index += 1
        if self.index >= len(self.steps):
            self.banner.destroy()
        else:
            self._show_step()
