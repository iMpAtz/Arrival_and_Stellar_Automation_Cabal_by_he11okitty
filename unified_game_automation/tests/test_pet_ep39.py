"""EP39 workflow regressions; no game attachment or real clicks."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.pet_automation import PetAutomation


class EP39Tests(unittest.TestCase):
    def make_automation(self, texts):
        core = Mock()
        core.stop_event = threading.Event()
        core.session = SimpleNamespace(dry_run=False)
        core.stop.side_effect = lambda *args: core.stop_event.set()
        core.sleep.side_effect = lambda seconds: not core.stop_event.is_set()
        game = Mock()
        game.is_connected.return_value = True
        game.click_at_position.return_value = True
        ocr = Mock()
        ocr.extract_text.side_effect = texts
        found = Mock()
        pet = PetAutomation(game, ocr, bot_core=core, on_target_found=found)
        pet.on_needs_review = Mock()
        pet.set_workflow_mode("ep39")
        pet.set_step_coords("EP39 Click 1", (10, 20))
        pet.set_step_coords("EP39 Click 2", (30, 40))
        pet.set_step_coords("EP39 Click 3", (50, 60))
        pet.set_ocr_area((0, 0, 100, 40))
        pet.set_ocr_targets(["Accuracy"])
        return pet, game, core, found

    def run_loop(self, texts):
        pet, game, core, found = self.make_automation(texts)
        pet.running = True
        pet._run_loop()
        self.assertFalse(pet.running)
        return pet, game, core, found

    def test_popup_target_cancels_before_stopping(self):
        _, game, core, found = self.run_loop(["Accuracy +1", "Accuracy +1"])
        self.assertEqual([c.args[0] for c in game.click_at_position.call_args_list],
                         [(10, 20), (50, 60)])
        core.stop.assert_called_with("target_found")
        found.assert_called_once()

    def test_two_clicks_then_ocr_stops_before_next_click_one(self):
        _, game, core, found = self.run_loop(["Defense +1", "Accuracy +1", "Accuracy +1"])
        self.assertEqual([c.args[0] for c in game.click_at_position.call_args_list],
                         [(10, 20), (30, 40), (10, 20), (50, 60)])
        core.stop.assert_called_with("target_found")
        found.assert_called_once()

    def test_blank_ocr_does_not_click_second_position(self):
        pet, game, core, _ = self.run_loop(["", "", ""])
        game.click_at_position.assert_called_once_with((10, 20))
        core.stop.assert_called_with("needs_review")
        pet.on_needs_review.assert_called_once()

    def test_target_with_extra_heading_still_stops(self):
        _, game, core, found = self.run_loop(["Pet Skill\nAccuracy +1"] * 2)
        self.assertEqual([c.args[0] for c in game.click_at_position.call_args_list],
                         [(10, 20), (50, 60)])
        core.stop.assert_called_with("target_found")
        found.assert_called_once()

    def test_wrapped_stat_is_recognized_without_losing_ignore_prefix(self):
        pet, _, _, _ = self.make_automation(["Ignore\nPenetration +1"] * 2)
        pet.set_ocr_targets(["Penetration"])
        self.assertFalse(pet._ocr_match_pet_targets()[0])
        self.assertTrue(pet._last_ocr_valid)
        pet.set_ocr_targets(["Ignore Penetration"])
        self.assertTrue(pet._ocr_match_pet_targets()[0])

    def test_unknown_stat_continues_until_a_selected_target(self):
        _, game, core, found = self.run_loop(
            ["Some new EP39 stat +20", "Accuracy +1", "Accuracy +1"])
        self.assertEqual([c.args[0] for c in game.click_at_position.call_args_list],
                         [(10, 20), (30, 40), (10, 20), (50, 60)])
        core.stop.assert_called_with("target_found")
        found.assert_called_once()

    def test_ocr_is_only_read_after_popup_opens(self):
        pet, game, core, _ = self.make_automation([])
        events = []
        game.click_at_position.side_effect = lambda pos: events.append(pos) or True
        pet.ocr_engine.extract_text.side_effect = lambda image: events.append("ocr") or "Some new stat +20"
        core.session.dry_run = True
        pet.running = True
        pet._run_loop()
        self.assertEqual(events, [(10, 20), "ocr", (30, 40)])

    def test_cancel_ignore_damage_reduction_can_be_selected(self):
        pet, game, core, found = self.make_automation(["Cancel Ignore Damage Reduction + 20"] * 2)
        pet.set_ocr_targets(["Cancel Ignore Damage Reduction"])
        pet.running = True
        pet._run_loop()
        self.assertEqual([c.args[0] for c in game.click_at_position.call_args_list],
                         [(10, 20), (50, 60)])
        core.stop.assert_called_with("target_found")

    def test_duration_stat_with_seconds_unit_is_matched_and_cancelled(self):
        target = "Aura Mode Duration Increase"
        for reading in ("Aura Mode Duration Increase 2s",
                        "Aura Mode Duration Increase + 2s"):
            with self.subTest(reading=reading):
                pet, game, core, found = self.make_automation([reading] * 2)
                pet.set_ocr_targets([target])
                pet.running = True
                pet._run_loop()
                self.assertEqual([call.args[0] for call in game.click_at_position.call_args_list],
                                 [(10, 20), (50, 60)])
                core.stop.assert_called_with("target_found")
                found.assert_called_once()

    def test_duration_stat_with_seconds_unit_is_clear_for_non_target(self):
        pet, _, _, _ = self.make_automation(["Aura Mode Duration Increase + 2s"])
        pet.set_ocr_targets(["Accuracy"])
        hit, _ = pet._ocr_match_pet_targets()
        self.assertFalse(hit)
        self.assertTrue(pet._last_ocr_valid)

    def test_stat_values_are_ignored_but_two_seconds_is_preserved(self):
        pet, _, _, _ = self.make_automation(["Resist Skill Amp 3"])
        pet.set_ocr_targets(["Resist Skill Amp."])
        hit, normalized = pet._ocr_match_pet_targets()
        self.assertTrue(hit)
        self.assertTrue(pet._last_ocr_valid)
        self.assertEqual(normalized, "resist skill amp")

        pet.ocr_engine.extract_text.side_effect = ["Aura Mode Duration Increase 2s"]
        pet.set_ocr_targets(["Aura Mode Duration"])
        _, normalized = pet._ocr_match_pet_targets()
        self.assertEqual(normalized, "aura mode duration increase 2s")

    def test_exact_catalog_stat_is_not_retried_for_low_word_confidence(self):
        class ReadingOCR:
            def extract_pet_reading(self, image):
                return "Resist Skill Amp 3", (("Resist", 91), ("Skill", 90),
                                               ("Amp", 24), ("3", 20))
        pet, game, core, found = self.make_automation([])
        pet.ocr_engine = ReadingOCR()
        pet.set_ocr_targets(["Resist Skill Amp"])
        pet.running = True
        pet._run_loop()
        self.assertEqual([call.args[0] for call in game.click_at_position.call_args_list],
                         [(10, 20), (50, 60)])
        core.stop.assert_called_with("target_found")
        found.assert_called_once()

    def test_numbers_in_catalog_names_are_ignored_for_ep39_matching(self):
        pet, _, _, _ = self.make_automation(["Drop 2 slot item 3"])
        pet.set_ocr_targets(["Drop 2 slot item"])
        hit, normalized = pet._ocr_match_pet_targets()
        self.assertTrue(hit)
        self.assertEqual(normalized, "drop slot item")

    def test_blank_ocr_reason_is_logged(self):
        _, _, core, _ = self.run_loop([""] * 3)
        self.assertTrue(any("OCR returned no text" in c.args[0]
                            for c in core.update_status.call_args_list))

    def test_pet_ocr_uses_enlarged_block_without_cache(self):
        from PIL import Image
        from core.ocr_engine import OCREngine
        engine = OCREngine()
        with patch.object(engine, "extract_text", return_value="Accuracy +1") as extract:
            self.assertEqual(engine.extract_pet_text(Image.new("RGB", (197, 48))), "Accuracy +1")
        self.assertEqual(extract.call_args.args[0].size, (591, 144))
        self.assertEqual(extract.call_args.kwargs, {"config": "--psm 6 --oem 1", "fresh": True})

    def test_stop_between_clicks_prevents_second_click(self):
        pet, game, core, _ = self.make_automation(["Defense +1"])
        game.click_at_position.side_effect = lambda pos: (core.stop_event.set() or True)
        pet.running = True
        pet._run_loop()
        game.click_at_position.assert_called_once_with((10, 20))

    def test_ep39_requires_three_positions(self):
        pet, _, _, _ = self.make_automation([])
        self.assertEqual(pet._validate_config(), (True, ""))
        pet.coords["ep39_click_3"] = None
        self.assertFalse(pet._validate_config()[0])
        pet.set_workflow_mode("standard")
        self.assertEqual(len(pet.get_step_keys()), 5)
        self.assertIn("pet_training", pet._validate_config()[1])

    def test_standard_keeps_five_click_sequence(self):
        pet, game, core, _ = self.make_automation(["Defense +1"] * 5)
        pet.set_workflow_mode("standard")
        for i, key in enumerate(pet.get_step_keys()):
            pet.coords[key] = (i, i)
        core.session.dry_run = True
        pet.running = True
        pet._run_loop()
        self.assertEqual([c.args[0] for c in game.click_at_position.call_args_list],
                         [(i, i) for i in range(5)])

    def test_cancel_happens_before_stop_and_notification(self):
        pet, game, core, found = self.make_automation(["Accuracy +1"] * 2)
        events = []
        game.click_at_position.side_effect = lambda pos: events.append(pos) or not core.stop_event.is_set()
        def stop(reason):
            events.append(reason)
            core.stop_event.set()
        core.stop.side_effect = stop
        found.side_effect = lambda *args: events.append("notification")
        pet.running = True
        pet._run_loop()
        self.assertEqual(events, [(10, 20), (50, 60), "target_found", "notification"])

    def test_cancel_failure_does_not_report_target_found(self):
        pet, game, core, found = self.make_automation(["Accuracy +1"] * 2)
        game.click_at_position.side_effect = [True, False]
        pet.running = True
        pet._run_loop()
        core.stop.assert_called_with("action_failed")
        found.assert_not_called()

    def test_noise_keeps_popup_open_and_notifies_once(self):
        for text in ["???", "xqztr +1", "A c c +1", "Accur@cy +1", "123", "Defense\n| !"]:
            with self.subTest(text=text):
                pet, game, core, found = self.run_loop([text] * 3)
                game.click_at_position.assert_called_once_with((10, 20))
                core.stop.assert_called_with("needs_review")
                pet.on_needs_review.assert_called_once()
                found.assert_not_called()

    def test_retry_recovers_to_clear_new_stat(self):
        pet, game, core, _ = self.make_automation(["", "xqztr", "Companion Recovery +20"])
        core.session.dry_run = True
        pet.running = True
        pet._run_loop()
        self.assertEqual([c.args[0] for c in game.click_at_position.call_args_list],
                         [(10, 20), (30, 40)])
        core.stop.assert_called_with("dry_run_complete")
        pet.on_needs_review.assert_not_called()

    def test_conflicting_target_confirmation_never_rolls(self):
        for texts in [["Accuracy +1", "Defense +1", "Defense +1"],
                      ["Accuracy +1", "", "Defense +1"]]:
            with self.subTest(texts=texts):
                pet, game, core, found = self.run_loop(texts)
                game.click_at_position.assert_called_once_with((10, 20))
                core.stop.assert_called_with("needs_review")
                found.assert_not_called()

    def test_numeric_values_do_not_change_target_confirmation(self):
        _, game, core, found = self.run_loop(
            ["Accuracy +1", "Accuracy +2", "Accuracy +3"])
        self.assertEqual([call.args[0] for call in game.click_at_position.call_args_list],
                         [(10, 20), (50, 60)])
        core.stop.assert_called_with("target_found")
        found.assert_called_once()

    def test_stop_during_confirmation_does_not_cancel_or_warn(self):
        pet, game, core, found = self.make_automation(["Accuracy +1"])
        def sleep(seconds):
            if seconds == 0.35:
                core.stop_event.set()
            return not core.stop_event.is_set()
        core.sleep.side_effect = sleep
        pet.running = True
        pet._run_loop()
        game.click_at_position.assert_called_once_with((10, 20))
        found.assert_not_called()
        pet.on_needs_review.assert_not_called()

    def test_word_confidence_rejects_garbled_names_but_accepts_clear_catalog_names(self):
        class ReadingOCR:
            def __init__(self, text, confidence):
                self.text, self.confidence = text, confidence
            def extract_pet_reading(self, image):
                return self.text, tuple((word, self.confidence) for word in self.text.split())
        for text, confidence, expected in [("Companion Recovery +20", 94, "dry_run_complete"),
                                           ("Accurcy +1", 23, "needs_review"),
                                           ("Accuracy +1", 23, "target_found"),
                                           ("xqztr +1", 98, "needs_review")]:
            with self.subTest(text=text, confidence=confidence):
                pet, game, core, found = self.make_automation([])
                pet.ocr_engine = ReadingOCR(text, confidence)
                core.session.dry_run = True
                pet.running = True
                pet._run_loop()
                core.stop.assert_called_with(expected)
                self.assertEqual(game.click_at_position.call_count,
                                 2 if expected in ("dry_run_complete", "target_found") else 1)

    def test_tesseract_reading_preserves_lines_and_confidence(self):
        from PIL import Image
        from core.ocr_engine import OCREngine
        engine = OCREngine()
        data = {"text": ["", "Companion", "Recovery", "+20"],
                "conf": [-1, 94, 92, 90], "page_num": [1]*4,
                "block_num": [1]*4, "par_num": [1]*4, "line_num": [0, 1, 1, 2]}
        with patch("core.ocr_engine.pytesseract.image_to_data", return_value=data) as extract:
            text, words = engine.extract_pet_reading(Image.new("RGB", (100, 30)))
        self.assertEqual(text, "Companion Recovery\n+20")
        self.assertEqual(words, (("Companion", 94.0), ("Recovery", 92.0), ("+20", 90.0)))
        self.assertEqual(extract.call_args.args[0].size, (300, 90))
        self.assertEqual(extract.call_args.kwargs["timeout"], engine.timeout_seconds)
        with patch("core.ocr_engine.pytesseract.image_to_data", side_effect=RuntimeError("timeout")):
            self.assertEqual(engine.extract_pet_reading(Image.new("RGB", (100, 30))), ("", ()))
        self.assertIn("timeout", engine.last_error)


class EP39UITests(unittest.TestCase):
    def test_visibility_readiness_and_config_roundtrip(self):
        import customtkinter as ctk
        from ui.pet_tab import PetTab
        root = ctk.CTk()
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as directory:
                config = str(Path(directory) / "pet_config.json")
                main = SimpleNamespace(game_connector=Mock(), ocr_engine=Mock(),
                                       bot_core=Mock(), update_status=Mock(), root=root)
                with patch.object(PetTab, "_get_config_path", return_value=config), \
                     patch("ui.pet_tab.messagebox.showinfo"):
                    tab = PetTab(root, main)
                    self.assertEqual(tab.workflow_mode_var.get(), "Standard")
                    tab.workflow_mode_var.set("EP39")
                    tab._on_workflow_changed("EP39")
                    visible = [s for s, row in tab.step_rows.items() if row.winfo_manager()]
                    self.assertEqual(visible, ["EP39 Click 1", "EP39 Click 2", "EP39 Click 3"])
                    for step, coords in zip(visible, [(10, 20), (30, 40), (50, 60)]):
                        tab.step_coords[step] = coords
                        tab.automation.set_step_coords(step, coords)
                    tab.ocr_area = (0, 0, 100, 40)
                    tab._check_enable_start()
                    self.assertEqual(tab.btn_start.cget("state"), "normal")
                    tab.ocr_check_vars["Accuracy"].set(True)
                    tab.save_config()
                    saved = json.loads(Path(config).read_text())
                    self.assertEqual(saved["workflow_mode"], "ep39")
                    loaded = PetTab(root, main)
                    self.assertEqual(loaded.automation.workflow_mode, "ep39")
                    self.assertEqual(loaded.automation.coords["ep39_click_2"], (30, 40))
                    self.assertEqual(loaded.automation.coords["ep39_click_3"], (50, 60))
                    self.assertTrue(loaded.ocr_check_vars["Accuracy"].get())
                    loaded.workflow_mode_var.set("Standard")
                    loaded._on_workflow_changed("Standard")
                    self.assertEqual(len([r for r in loaded.step_rows.values() if r.winfo_manager()]), 5)
                    self.assertEqual(loaded.btn_start.cget("state"), "disabled")
                    # Old EP39 profiles cannot start until Cancel is calibrated.
                    saved["schema_version"] = 2
                    saved["step_coords"].pop("EP39 Click 3")
                    Path(config).write_text(json.dumps(saved), encoding="utf-8")
                    legacy = PetTab(root, main)
                    self.assertEqual(legacy.btn_start.cget("state"), "disabled")
                    self.assertIsNone(legacy.automation.coords["ep39_click_3"])
        finally:
            root.destroy()

    def test_review_warning_is_queued_and_restores_controls(self):
        from ui.pet_tab import PetTab
        tab = PetTab.__new__(PetTab)
        tab._check_enable_start = Mock()
        tab.btn_stop = Mock()
        tab.main_window = SimpleNamespace(post_run_ui=Mock(), clear_running_tool=Mock())
        with patch("ui.pet_tab.messagebox.showwarning") as warning:
            tab.on_needs_review("Unclear OCR", "xqztr")
            warning.assert_not_called()
            tab.main_window.post_run_ui.call_args.args[0]()
            warning.assert_called_once()
            self.assertIn("xqztr", warning.call_args.args[1])
            tab.btn_stop.configure.assert_called_with(state="disabled")
            tab._check_enable_start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
