"""Pet Workbench inspection and portable OCR settings without game input."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.pet_automation import PetAutomation
from core.profiles import export_profile, import_profile
from data.pet_data import PET_CONFIG_KEYS, PET_CONFIG_VERSION
from ui.workbench_tab import WorkbenchTab


class WorkbenchPetTests(unittest.TestCase):
    def make_workbench(self, text, name="Pet EP39"):
        engine = Mock()
        engine.extract_text.return_value = text
        connector = Mock()
        auto = PetAutomation(connector, engine)
        auto.set_ocr_area((1, 2, 100, 40))
        auto.coords.update({"pet_training": (5, 6), "ep39_click_1": (10, 20),
                            "ep39_click_2": (30, 40), "ep39_click_3": (50, 60)})
        pet_tab = SimpleNamespace(automation=auto, _get_selected_ocr_targets=lambda: ["Accuracy"])
        bench = WorkbenchTab.__new__(WorkbenchTab)
        bench.main = SimpleNamespace(pet_tab=pet_tab, arrival_tab=None, stellar_tab=None,
                                     ocr_engine=engine, game_connector=connector,
                                     post_ui=lambda callback: callback())
        bench.tool = Mock()
        bench.tool.get.return_value = name
        bench.display_image = Mock()
        bench.show = Mock()
        bench.idle = Mock(return_value=True)
        bench._busy = False
        return bench, auto, connector

    def inspect_now(self, bench):
        with patch("ui.workbench_tab.threading.Thread") as thread:
            thread.side_effect = lambda target, **kwargs: SimpleNamespace(start=target)
            bench.inspect(Image.new("RGB", (100, 40)))
        self.assertFalse(bench._busy)
        return bench.show.call_args.args[0]

    def test_ep39_accepts_new_clear_names_without_changing_live_workflow(self):
        bench, auto, connector = self.make_workbench("Companion Recovery +20")
        result = self.inspect_now(bench)
        self.assertEqual(result["decision"], "absent")
        self.assertEqual(result["workflow"], "ep39")
        self.assertIn("OK", result["next_step"])
        self.assertEqual(auto.workflow_mode, "standard")
        connector.click_at_position.assert_not_called()

    def test_standard_still_requires_catalog_names(self):
        bench, _, _ = self.make_workbench("Companion Recovery +20", "Pet OCR")
        self.assertEqual(self.inspect_now(bench)["decision"], "unknown")

    def test_inspection_reads_without_targets_for_both_pet_workflows(self):
        for name in ("Pet OCR", "Pet EP39"):
            with self.subTest(name=name):
                bench, auto, connector = self.make_workbench("Accuracy +1", name)
                bench.main.pet_tab._get_selected_ocr_targets = lambda: []
                result = self.inspect_now(bench)
                self.assertEqual(result["text"], "Accuracy +1")
                self.assertEqual(result["decision"], "no_targets")
                self.assertFalse(result["targets_selected"])
                bench.main.ocr_engine.extract_text.assert_called_once()
                connector.click_at_position.assert_not_called()

    def test_raw_text_preserves_symbols_case_and_lines(self):
        bench, _, _ = self.make_workbench("Accuracy +1\nDefense +2")
        result = self.inspect_now(bench)
        self.assertEqual(result["text"], "Accuracy +1\nDefense +2")
        self.assertEqual(result["normalized_text"], "accuracy defense")

    def test_empty_ocr_shows_error_and_crop_details(self):
        bench, _, _ = self.make_workbench("")
        bench.main.ocr_engine.last_error = "Tesseract process timeout"
        bench.main.ocr_engine.diagnostics.return_value = {"tesseract": True}
        result = self.inspect_now(bench)
        self.assertEqual(result["text"], "")
        self.assertEqual(result["issue"], "Tesseract process timeout")
        self.assertEqual(result["crop_size"], [100, 40])
        self.assertEqual(result["ocr_diagnostics"], {"tesseract": True})

    def test_live_observation_still_requires_targets(self):
        bench, auto, _ = self.make_workbench("Accuracy +1")
        self.assertEqual(auto._ocr_match_pet_targets(), (False, ""))
        self.assertEqual(auto._last_ocr_issue, "No OCR targets selected")
        bench.main.ocr_engine.extract_text.assert_not_called()

    def test_ep39_target_is_not_claimed_confirmed_by_one_read(self):
        bench, _, connector = self.make_workbench("Accuracy +1")
        result = self.inspect_now(bench)
        self.assertEqual(result["decision"], "matched")
        self.assertIn("Confirm OCR again", result["next_step"])
        connector.click_at_position.assert_not_called()

    def test_ep39_unclear_and_empty_text_requests_review(self):
        for raw in ("", "xqztr +1"):
            with self.subTest(raw=raw):
                bench, _, connector = self.make_workbench(raw)
                result = self.inspect_now(bench)
                self.assertEqual(result["decision"], "unknown")
                self.assertIn("needs_review", result["next_step"])
                connector.click_at_position.assert_not_called()

    def test_preview_only_marks_selected_workflow_positions(self):
        for name, expected in (("Pet EP39", {"ep39_click_1", "ep39_click_2", "ep39_click_3"}),
                               ("Pet OCR", {"pet_training"})):
            with self.subTest(name=name):
                bench, _, connector = self.make_workbench("", name)
                connector.take_screenshot.return_value = Image.new("RGB", (200, 100))
                connector.get_window_rect.return_value = SimpleNamespace(left=0, top=0)
                connector.resolve_area.return_value = (1, 2, 100, 40)
                with patch("ui.workbench_tab.ImageDraw.Draw") as draw:
                    bench.preview()
                self.assertEqual({call.args[1] for call in draw.return_value.text.call_args_list}, expected)
                connector.click_at_position.assert_not_called()

    def test_live_crop_uses_pet_region_without_input(self):
        bench, auto, connector = self.make_workbench("")
        bench.inspect = Mock()
        bench.read_live()
        connector.take_screenshot.assert_called_once_with(auto.ocr_area)
        bench.inspect.assert_called_once_with(connector.take_screenshot.return_value)
        connector.click_at_position.assert_not_called()


class PetProfileTests(unittest.TestCase):
    def test_old_and_current_profiles_keep_ocr_and_drop_obsolete_fields(self):
        for version in range(1, PET_CONFIG_VERSION + 1):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                settings = {"schema_version": version, "workflow_mode": "ep39",
                            "ocr_area": [0, 0, 100, 40], "delay_ms": "800",
                            "step_coords": {"EP39 Click 3": [50, 60]},
                            "selected_ocr_options": ["Accuracy"],
                            "obsolete_detector_asset": "missing_model.bin",
                            "detection_mode": "retired"}
                source = root / "profile.json"
                source.write_text(json.dumps({"schema_version": 1, "settings": {"pet_config.json": settings}}))
                import_profile(source, root / "data")
                saved = json.loads((root / "data/pet_config.json").read_text())
                self.assertLessEqual(set(saved), PET_CONFIG_KEYS)
                self.assertEqual(saved["schema_version"], PET_CONFIG_VERSION)
                self.assertEqual(saved["step_coords"], settings["step_coords"])
                self.assertEqual(saved["selected_ocr_options"], ["Accuracy"])
                # Export also cleans old settings before considering assets.
                (root / "data/pet_config.json").write_text(json.dumps(settings))
                export_profile(root / "data", root / "export.json")
                exported = json.loads((root / "export.json").read_text())["settings"]["pet_config.json"]
                self.assertEqual(exported, saved)

    def test_future_pet_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "profile.json"
            source.write_text(json.dumps({"schema_version": 1, "settings": {
                "pet_config.json": {"schema_version": PET_CONFIG_VERSION + 1}}}))
            with self.assertRaises(ValueError):
                import_profile(source, root / "data")
            self.assertFalse((root / "data").exists())


if __name__ == "__main__":
    unittest.main()
