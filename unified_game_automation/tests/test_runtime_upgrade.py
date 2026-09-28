import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from core.bot_core import BotCore
from core.game_connector import GameConnector
from core.observations import parse_stats, evaluate
from core.ocr_engine import OCREngine
from core.profiles import export_profile, import_profile
from core.template_matcher import TemplateMatcher
from automation.arrival_automation import ArrivalAutomation
from data.arrival_data import get_all_base_stat_names
from data.stellar_data import get_stellar_options


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.core = BotCore(status_callback=lambda message: None)
        self.core.report_dir = Path(self.directory.name)

    def test_cancellation_is_not_reused_and_restart_waits_for_exit(self):
        entered, release = threading.Event(), threading.Event()
        self.assertTrue(self.core.begin_run("old"))
        old_event = self.core.stop_event
        def worker():
            entered.set()
            release.wait(2)
            self.assertIs(self.core.stop_event, old_event)
        thread = self.core.register_thread("worker", worker)
        self.assertTrue(entered.wait(1))
        self.core.emergency_stop()
        self.assertFalse(self.core.begin_run("new"))
        release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertTrue(self.core.begin_run("new"))
        self.assertIsNot(self.core.stop_event, old_event)
        self.assertTrue(old_event.is_set())
        self.core.end_run()

    def test_stop_does_not_join_blocking_worker(self):
        release = threading.Event()
        self.core.begin_run("blocking")
        thread = self.core.register_thread("blocking", lambda: release.wait(2))
        started = time.monotonic()
        self.core.stop()
        self.assertLess(time.monotonic()-started, 0.1)
        release.set()
        thread.join(2)
        self.assertFalse(self.core.is_busy())

    def test_watchdog_completion_and_report(self):
        self.core.begin_run("stall")
        session = self.core.session
        self.core.start_watchdog(0.03, 0.01)
        thread = self.core.register_thread("stall", lambda: session.cancel.wait(1))
        thread.join(2)
        self.assertFalse(self.core.is_busy())
        report = self.core.completed_runs.get(timeout=1)
        self.assertEqual(report["stop_reason"], "watchdog_timeout")
        self.assertEqual(json.loads(next(self.core.report_dir.glob("*.json")).read_text())["run_id"], session.run_id)

    def test_long_interruptible_wait_does_not_trip_stall_watchdog(self):
        self.core.begin_run("waiting")
        self.core.start_watchdog(0.15, 0.01)
        thread = self.core.register_thread("waiting", lambda: self.core.sleep(0.3))
        thread.join(1)
        self.assertEqual(self.core.completed_runs.get(timeout=1)["stop_reason"], "completed")

    def test_all_mouse_paths_obey_dry_run_and_action_limit(self):
        connector = GameConnector()
        connector.game_window = Mock()
        connector.input_policy = self.core.authorize_input
        self.core.dry_run = True
        self.core.max_actions = 2
        self.core.begin_run("test")
        results = []
        def work():
            results.append(connector.click_at_position((10, 20)))
            results.append(connector.double_click_at_position((10, 20)))
            results.append(connector.right_click_at_position((10, 20)))
        thread = self.core.register_thread("input", work)
        thread.join(1)
        self.assertEqual(results, [True, True, False])
        self.assertEqual(connector.game_window.mock_calls, [])
        self.assertEqual(self.core.session.stop_reason, "action_limit")

    def test_background_click_cannot_interrupt_exclusive_run(self):
        connector = GameConnector()
        connector.game_window = Mock()
        connector.input_policy = self.core.authorize_input
        self.core.begin_run("Arrival")
        self.assertFalse(connector.middle_click_at_position((10, 20)))
        self.assertEqual(connector.game_window.mock_calls, [])
        self.core.end_run()

    def test_region_follows_window_and_rejects_resize(self):
        connector = GameConnector()
        with patch.object(connector, "get_client_rect", return_value=(100, 200, 900, 800)):
            area = connector.screen_to_client_area((120, 240, 100, 80))
        with patch.object(connector, "get_client_rect", return_value=(-800, 50, 0, 650)):
            self.assertEqual(connector.resolve_area(area), (-780, 90, 100, 80))
        with patch.object(connector, "get_client_rect", return_value=(100, 200, 1000, 800)):
            self.assertIsNone(connector.resolve_area(area))

    def test_parser_thousands_and_alias_exclusion(self):
        observation = parse_stats("Absorb Damage +1,200\nDefense +400", get_all_base_stat_names())
        self.assertTrue(observation.valid)
        self.assertEqual(observation.stats[0].value, 1200)
        for text in ("Ignore Penetration +15", "Cancel Ignore Penetration +15", "PVE Penetration +15"):
            reading = parse_stats(text, get_stellar_options(), stellar=True)
            self.assertEqual(evaluate(reading, [("Penetration", 15)]), "absent")
        reading = parse_stats("Pene tration +15", get_stellar_options(), stellar=True)
        self.assertEqual(evaluate(reading, [("Penetration", 15)]), "matched")

    def test_missing_or_decimal_values_are_unknown(self):
        for text in ("Defense", "Defense +1.5", "Defense +1,20", "", "Defense +10\nUnexpected dialog"):
            reading = parse_stats(text, get_all_base_stat_names())
            self.assertEqual(evaluate(reading, [("Defense", 1)]), "unknown", text)

    def test_arrival_unknown_does_not_click_and_retains_stats(self):
        connector = Mock()
        connector.is_connected.return_value = True
        connector.capture_area_bitblt.return_value = Image.new("RGB", (20, 20))
        ocr = Mock()
        ocr.extract_text.return_value = ""
        auto = ArrivalAutomation(connector, ocr, bot_core=self.core)
        auto.area = (0, 0, 20, 20)
        auto.apply_button_coords, auto.change_button_coords = (1, 2), (3, 4)
        auto.safe_sleep_ms = lambda *args: not self.core.stop_event.is_set()
        self.core.begin_run("Arrival Skill", auto)
        self.assertTrue(auto.start({"defensive": [("Defense", 200, "200")]}))
        report = self.core.completed_runs.get(timeout=2)
        connector.click_at_position.assert_not_called()
        self.assertEqual(report["stop_reason"], "needs_review")
        auto.stat_counter = {"Defense +100": 3}
        auto.stop()
        self.assertEqual(auto.stat_counter, {"Defense +100": 3})

    def test_arrival_success_requires_two_readings_without_initial_reroll(self):
        connector = Mock()
        connector.is_connected.return_value = True
        connector.capture_area_bitblt.return_value = Image.new("RGB", (20, 20))
        ocr = Mock()
        ocr.extract_text.return_value = "Defense +400"
        auto = ArrivalAutomation(connector, ocr, bot_core=self.core)
        auto.area, auto.apply_button_coords, auto.change_button_coords = (0, 0, 20, 20), (1, 2), (3, 4)
        auto.safe_sleep_ms = lambda *args: True
        self.core.begin_run("Arrival Skill", auto)
        auto.start({"defensive": [("Defense", 200, "200")]})
        report = self.core.completed_runs.get(timeout=2)
        self.assertEqual(report["stop_reason"], "target_found")
        self.assertEqual(ocr.extract_text.call_count, 2)
        connector.click_at_position.assert_not_called()
        self.assertEqual(report["statistics"], {"Defense +400": 1})

    def test_exact_cache_invalidates_on_changed_digit_and_fresh_read(self):
        engine = OCREngine()
        first = Image.new("RGB", (20, 20), "white")
        second = first.copy()
        second.putpixel((1, 1), (0, 0, 0))
        with patch("core.ocr_engine.pytesseract.image_to_string", side_effect=["15", "16", "16"] ) as extract:
            self.assertEqual(engine.extract_text(first), "15")
            self.assertEqual(engine.extract_text(first), "15")
            self.assertEqual(engine.extract_text(second), "16")
            self.assertEqual(engine.extract_text(second, fresh=True), "16")
            self.assertEqual(extract.call_count, 3)

    def test_real_tesseract_from_workspace_with_spaces(self):
        engine = OCREngine()
        image = Image.new("RGB", (400, 80), "white")
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
        ImageDraw.Draw(image).text((10, 10), "Defense +400", font=font, fill="black")
        text = engine.extract_text(image, "--psm 7", fresh=True)
        self.assertEqual(engine.last_error, "")
        self.assertIn("400", text)

    def test_profile_portability_and_path_traversal_rejection(self):
        root = Path(self.directory.name)
        source, bundle, target = root/"source", root/"bundle", root/"target"
        source.mkdir(); bundle.mkdir()
        asset = source/"template.png"
        Image.new("RGB", (3, 3)).save(asset)
        (source/"image_clicker_config.json").write_text(json.dumps({"images": [{"file_path": str(asset)}]}))
        export_profile(source, bundle/"profile.json")
        import_profile(bundle/"profile.json", target)
        imported = json.loads((target/"image_clicker_config.json").read_text())
        self.assertTrue(Path(imported["images"][0]["file_path"]).is_file())
        (bundle/"bad.json").write_text(json.dumps({"schema_version": 1, "settings": {"../outside.json": {}}}))
        with self.assertRaises(ValueError):
            import_profile(bundle/"bad.json", target)

    def test_multiscale_template_matching_and_flat_template(self):
        import cv2
        rng = np.random.default_rng(7)
        template = rng.integers(0, 255, size=(20, 20), dtype=np.uint8)
        screen = np.zeros((100, 100), dtype=np.uint8)
        screen[30:54, 40:64] = cv2.resize(template, (24, 24))
        matcher = TemplateMatcher()
        score, point, dimensions = matcher.match(screen, template, 1.0, 1.2)
        self.assertGreater(score, 0.99)
        self.assertEqual(point, (40, 30))
        self.assertEqual(dimensions, (24, 24))
        self.assertIsNone(matcher.match(screen, np.zeros((10, 10), dtype=np.uint8)))

    def test_gdi_resources_released_when_bitblt_fails(self):
        connector = GameConnector()
        connector.game_window = Mock(handle=123)
        source_dc, target_dc, bitmap = Mock(), Mock(), Mock()
        old_bitmap = object()
        source_dc.CreateCompatibleDC.return_value = target_dc
        target_dc.SelectObject.return_value = old_bitmap
        with patch.object(connector, "is_connected", return_value=True), \
                patch("core.game_connector.win32gui.IsIconic", return_value=False), \
                patch("core.game_connector.win32gui.GetWindowRect", return_value=(0, 0, 100, 100)), \
                patch("core.game_connector.win32gui.GetWindowDC", return_value=456), \
                patch("core.game_connector.win32ui.CreateDCFromHandle", return_value=source_dc), \
                patch("core.game_connector.win32ui.CreateBitmap", return_value=bitmap), \
                patch("core.game_connector.windll.gdi32.BitBlt", return_value=0), \
                patch("core.game_connector.win32gui.DeleteObject") as delete, \
                patch("core.game_connector.win32gui.ReleaseDC") as release:
            self.assertIsNone(connector.capture_area_bitblt((0, 0, 50, 50)))
        target_dc.SelectObject.assert_any_call(old_bitmap)
        target_dc.DeleteDC.assert_called_once()
        source_dc.DeleteDC.assert_called_once()
        delete.assert_called_once_with(bitmap.GetHandle())
        release.assert_called_once_with(123, 456)

    def test_pet_does_not_confuse_cancel_ignore_with_ignore(self):
        from automation.pet_automation import PetAutomation
        connector, engine = Mock(), Mock()
        engine.extract_text.return_value = "Cancel Ignore Penetration +50"
        auto = PetAutomation(connector, engine)
        auto.set_area((0, 0, 10, 10))
        auto.set_ocr_targets(["Ignore Penetration"])
        matched, _ = auto._ocr_match_pet_targets()
        self.assertFalse(matched)
        self.assertTrue(auto._last_ocr_valid)

    def test_background_session_keeps_its_own_dry_run_and_limits(self):
        from core.session import RunSession
        session = RunSession("Image Clicker", dry_run=True, max_actions=1)
        self.core.bind_background(session)
        self.assertEqual(self.core.authorize_input(), (True, True))
        self.assertEqual(self.core.authorize_input(), (False, False))
        self.assertEqual(session.stop_reason, "action_limit")


if __name__ == "__main__":
    unittest.main(verbosity=2)
