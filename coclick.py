"""Deprecated entry point.

The bot logic now lives in ``bot_engine.py`` (as ``BotEngine``) and the control
UI in ``gui.py``. Run the app with ``python main.py`` (or the packaged
``CoClick.exe``). This shim is kept so ``python coclick.py`` still opens the GUI.
"""

from gui import App

if __name__ == "__main__":
    print("coclick.py is deprecated — launching the CoClick GUI (see main.py).")
    App().run()
