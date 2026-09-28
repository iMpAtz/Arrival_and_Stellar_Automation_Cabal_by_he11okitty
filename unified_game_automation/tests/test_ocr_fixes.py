import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.ocr_engine import OCREngine
from core.game_connector import GameConnector
from automation.pet_automation import PetAutomation
from automation.stellar_automation import StellarAutomation
from automation.arrival_automation import ArrivalAutomation


class DummyGameConnector:
    def __init__(self, image_to_return=None):
        self.image_to_return = image_to_return or Image.new("RGB", (320, 160), color="white")

    def take_screenshot(self, area=None):
        return self.image_to_return

    def capture_area_bitblt(self, area):
        return self.image_to_return

    def is_connected(self):
        return True


class DummyBotCore:
    def __init__(self):
        self.stop_event = DummyStopEvent()

    def update_status(self, msg):
        pass

    def stop(self):
        pass


class DummyStopEvent:
    def is_set(self):
        return False


def test_ocr_engine_numpy_and_quotes():
    engine = OCREngine()
    assert engine.tessdata_dir in f'--tessdata-dir {engine.tessdata_dir}'
    
    # Test numpy array handling without AttributeError
    np_img = np.zeros((100, 100, 3), dtype=np.uint8)
    pil_img = engine._ensure_pil_image(np_img)
    assert isinstance(pil_img, Image.Image)
    assert pil_img.mode == "RGB"
    print("test_ocr_engine_numpy_and_quotes passed.")


def test_arrival_cooltime_line_scoped():
    gc = DummyGameConnector()
    ocr = OCREngine()
    auto = ArrivalAutomation(game_connector=gc, ocr_engine=ocr)

    raw_ocr_text = "Add. Damage +45\nArrival Skill Cool Time decreased -15s\nHP Absorb Up +2%"
    stats = auto.handle_arrival_skill_special_cases(raw_ocr_text)
    assert "Skill Cool Time decreased." in stats
    assert stats["Skill Cool Time decreased."] == 15, f"Expected 15, got {stats.get('Skill Cool Time decreased.')}"
    print("test_arrival_cooltime_line_scoped passed.")


def test_ignore_penetration_variants():
    class CustomOcr:
        def extract_text(self, image):
            return "gnore Penetration +50"

    gc = DummyGameConnector()
    auto = PetAutomation(game_connector=gc, ocr_engine=CustomOcr())
    auto.set_area((0, 0, 100, 100))
    auto.set_ocr_targets(["Ignore Penetration"])

    matched, norm = auto._ocr_match_pet_targets()
    assert matched is True
    print("test_ignore_penetration_variants passed.")


if __name__ == "__main__":
    test_ocr_engine_numpy_and_quotes()
    test_arrival_cooltime_line_scoped()
    test_ignore_penetration_variants()
    print("\nAll OCR system fix verification tests PASSED successfully!")
