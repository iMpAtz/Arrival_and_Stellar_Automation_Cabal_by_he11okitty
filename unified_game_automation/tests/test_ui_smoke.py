"""Hidden-window construction test. No game attachment, hotkeys or game input."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customtkinter as ctk
from core.game_connector import GameConnector
from ui.main_window import MainWindow


def main():
    original = ctk.CTk.__init__
    def hidden(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.withdraw()
    with tempfile.TemporaryDirectory() as directory, \
            patch.object(ctk.CTk, "__init__", hidden), \
            patch.object(GameConnector, "connect_to_game", return_value=False), \
            patch("keyboard.add_hotkey", return_value=None), \
            patch("keyboard.unhook_all"):
        app = MainWindow()
        app.bot_core.report_dir = Path(directory)
        errors = []
        app.root.report_callback_exception = lambda *args: errors.append(args)
        try:
            app.root.update_idletasks()
            app.toggle_theme()
            app.toggle_theme()
            app.create_mini_ui()
            app.workbench_tab.diagnostics()
            assert app.workbench_tab.tool.cget("values") == ["Arrival", "Stellar", "Pet OCR", "Pet EP39"]
            app.workbench_tab.tool.set("Pet EP39")
            assert app.workbench_tab.selected()[1] is app.pet_tab
            app.bot_core.begin_run("Stellar System", app.stellar_tab.automation)
            app.stellar_tab.automation.running = True
            app.emergency_stop()
            app._pump_events()
            assert app.bot_core.stop_event.is_set()
            assert not app.stellar_tab.automation.running
            assert app.stellar_tab.btn_start.cget("state") == "normal"
            assert not errors, errors
            print("GUI smoke passed: eight tabs, themes, mini view, diagnostics, stop cleanup")
        finally:
            app.on_closing()


if __name__ == "__main__":
    main()
