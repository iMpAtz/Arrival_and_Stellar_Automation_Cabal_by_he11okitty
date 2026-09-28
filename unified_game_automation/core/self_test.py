"""Packaged runtime check: construct hidden UI and run OCR without game input."""
import json
from unittest.mock import patch
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
from core.game_connector import GameConnector


def run():
    from ui.main_window import MainWindow
    original = ctk.CTk.__init__
    def hidden(root, *args, **kwargs):
        original(root, *args, **kwargs)
        root.withdraw()
    with patch.object(ctk.CTk, "__init__", hidden), \
            patch.object(GameConnector, "connect_to_game", return_value=False), \
            patch("keyboard.add_hotkey", return_value=None), patch("keyboard.unhook_all"):
        app = MainWindow()
        try:
            app.root.update_idletasks()
            image = Image.new("RGB", (400, 80), "white")
            ImageDraw.Draw(image).text((10, 10), "Defense +400", fill="black",
                                      font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36))
            result = app.ocr_engine.extract_text(image, "--psm 7", fresh=True)
            if "400" not in result or app.ocr_engine.last_error:
                raise RuntimeError(f"OCR runtime check failed: {app.ocr_engine.last_error}; {result!r}")
            print("SELF_TEST_OK " + json.dumps({"ocr": result.strip(),
                                                "tabs": len(app.tabview._tab_dict),
                                                "macro": hasattr(app, "macro_tab"),
                                                "game_input": False}))
        finally:
            app.on_closing()
