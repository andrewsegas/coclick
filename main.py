"""CoClick entry point (PyInstaller target). Launches the GUI."""

from gui import App


def main():
    App().run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Windowed builds have no console, so an uncaught error would just make
        # the app vanish. Log it and show a dialog so a non-technical user can
        # report what happened.
        import os
        import tempfile
        import traceback

        details = traceback.format_exc()
        log_path = os.path.join(tempfile.gettempdir(), "coclick_error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(details)
        except OSError:
            pass
        try:
            import tkinter.messagebox as mb

            mb.showerror(
                "CoClick error",
                "CoClick hit an error and needs to close.\n\n"
                f"Details were saved to:\n{log_path}\n\n{details}",
            )
        except Exception:
            pass
        raise
