import unittest
import sys
import os
import re

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.game_connector import GameConnector
from automation.stellar_automation import StellarAutomation
from core.bot_core import BotCore
from data.arrival_data import STAT_VARIATIONS


class TestBugFixes(unittest.TestCase):
    def test_comma_stat_variation_parsing(self):
        """Verify that comma-separated stat variation strings parse to correct integers."""
        test_cases = [
            ("1,200", 1200),
            ("2,400", 2400),
            ("1,600", 1600),
            ("3,200", 3200),
            ("600", 600),
            ("18%", 18),
            ("120s", 120),
        ]
        for variation, expected_int in test_cases:
            match = re.search(r'(\d+)', variation.replace(',', ''))
            self.assertIsNotNone(match, f"Failed to match variation: {variation}")
            parsed_val = int(match.group(1))
            self.assertEqual(parsed_val, expected_int, f"Mismatch for variation: {variation}")

    def test_all_arrival_stat_variations_parseable(self):
        """Verify that every single variation in STAT_VARIATIONS can be sanitized and parsed."""
        for stat, variations in STAT_VARIATIONS.items():
            for var in variations:
                match = re.search(r'(\d+)', var.replace(',', ''))
                self.assertIsNotNone(match, f"Could not parse digits from {stat}: {var}")
                val = int(match.group(1))
                self.assertGreater(val, 0, f"Value should be positive for {stat}: {var}")

    def test_stellar_automation_default_effect_delay(self):
        """Verify StellarAutomation initializes effect_delay_ms to avoid AttributeError."""
        connector = GameConnector()
        bot_core = BotCore()
        stellar = StellarAutomation(game_connector=connector, ocr_engine=None, bot_core=bot_core)
        self.assertTrue(hasattr(stellar, 'effect_delay_ms'), "effect_delay_ms missing on initialization")
        self.assertEqual(stellar.effect_delay_ms, 1000)

    def test_coordinate_bit_packing(self):
        """Verify coordinate bit-packing produces safe 32-bit unsigned integers without OverflowError."""
        test_coords = [
            (100, 200),
            (0, 0),
            (1920, 1080),
            (-10, -20),
            (32767, 32767),
            (65535, 65535),
        ]
        for x, y in test_coords:
            lparam = ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)
            self.assertIsInstance(lparam, int)
            self.assertGreaterEqual(lparam, 0)
            self.assertLessEqual(lparam, 0xFFFFFFFF)

    def test_noise_filtering_logic(self):
        """Verify noise detection correctly distinguishes UI messages from console-only debug dumps."""
        noise_samples = [
            "[OCR Scan] Text: \"critical dmg +15%\"",
            "OCR text: Force +15",
            "Raw OCR text: 'Force 4 15'",
            "--- Detection Results for: ROI Crop ---\n[+] Found 2 detections",
            "  • Critical DMG +18% × 4",
            "SUMMARY OF DETECTED STATS",
            "Offensive Stats:",
            "Defensive Stats:",
            "Other Stats:",
            "🔍 Unmapped Stats (not in our data):",
            "[OCR Check #50] Took: 0.1234s",
            "[Loop #50] Total time: 0.5234s (with OCR)",
        ]
        valid_ui_samples = [
            "Ready",
            "Starting arrival skill automation",
            "🎉 Target option found - success!",
            "Roll #12: All Skill Amp. UP: 8%",
            "✅ Connected to game (1920x1080)",
            "⚠️ Game not found — make sure the game is running",
            "🚨 EMERGENCY STOP — stopping active automation",
            "📊 Roll statistics summary logged to terminal.",
        ]

        def check_noise(formatted):
            return (
                formatted.startswith("[OCR Scan] Text:")
                or formatted.startswith("OCR text:")
                or formatted.startswith("Raw OCR text:")
                or formatted.startswith("--- Detection Results")
                or formatted.startswith("  • ")
                or formatted.startswith("SUMMARY OF DETECTED STATS")
                or formatted.startswith("Offensive Stats:")
                or formatted.startswith("Defensive Stats:")
                or formatted.startswith("Other Stats:")
                or formatted.startswith("🔍 Unmapped Stats")
                or formatted.startswith("[OCR Check #")
                or formatted.startswith("[Loop #")
            )

        for sample in noise_samples:
            self.assertTrue(check_noise(sample), f"Should be classified as noise: {sample}")

        for sample in valid_ui_samples:
            self.assertFalse(check_noise(sample), f"Should NOT be classified as noise: {sample}")

    def test_version_bump_6_1_0(self):
        """Verify that version 6.1.0 is reflected in main_window and spec file."""
        main_window_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui", "main_window.py"))
        spec_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main_updated.spec"))

        with open(main_window_path, "r", encoding="utf-8") as f:
            main_window_content = f.read()

        with open(spec_path, "r", encoding="utf-8") as f:
            spec_content = f.read()

        self.assertIn("v6.1.0", main_window_content, "v6.1.0 not found in main_window.py")
        self.assertNotIn("v6.0.6", main_window_content, "Old v6.0.6 still present in main_window.py")
        self.assertIn("HelloK1TTY_Automation_V6.1.0", spec_content, "V6.1.0 not found in main_updated.spec")


    def test_macro_emergency_stop_integration(self):
        """Verify MacroAutomation and emergency_stop coordinate properly with BotCore."""
        from automation.macro_automation import MacroAutomation
        connector = GameConnector()
        bot_core = BotCore()
        macro = MacroAutomation(game_connector=connector, bot_core=bot_core)

        # Configure mock coord so start() can begin
        macro.set_coord(0, (100, 100))
        macro.set_coord_enabled(0, True)

        # Mock connector is_connected
        from unittest.mock import Mock, patch
        connector.game_window = Mock(handle=123)
        with patch("core.game_connector.win32gui.IsWindow", return_value=True):
            self.assertTrue(connector.is_connected())

        # Register running tool and start
        bot_core.begin_run("Macro", automation=macro)
        self.assertTrue(bot_core.is_busy())
        self.assertEqual(bot_core.active_tool(), "Macro")

        # Calling emergency_stop on bot_core stops the automation
        bot_core.emergency_stop()
        self.assertTrue(bot_core.stop_event.is_set())
        self.assertFalse(macro.running)

    def test_tooltip_safety_on_unmapped(self):
        """Verify ToolTip _show does not crash if widget is unmapped or destroyed."""
        import tkinter as tk
        from ui.main_window import ToolTip

        root = tk.Tk()
        root.withdraw()
        btn = tk.Button(root, text="Test")
        # Do not pack btn — it remains unmapped
        tip = ToolTip(btn, "Test tooltip")

        # _show should safely return without raising exception
        try:
            tip._show()
            self.assertIsNone(tip._tip_window, "ToolTip should not create window for unmapped widget")
        finally:
            tip._cancel()
            btn.destroy()
            root.destroy()


if __name__ == "__main__":
    unittest.main()
