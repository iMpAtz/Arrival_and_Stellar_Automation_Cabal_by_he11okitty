import sys
from pathlib import Path
import numpy as np
from PIL import Image

# Ensure project package can be imported
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.pet_automation import PetAutomation


class DummyGameConnector:
    def __init__(self, image_to_return=None):
        self.image_to_return = image_to_return or Image.new("RGB", (640, 640), color="white")
        self.captured_areas = []

    def take_screenshot(self, area):
        self.captured_areas.append(area)
        return self.image_to_return


class DummyBotCore:
    def __init__(self):
        self.stop_event = DummyStopEvent()
        self.status_messages = []

    def update_status(self, msg):
        self.status_messages.append(msg)

    def stop(self):
        pass

    def end_run(self, tool_name=""):
        pass


class DummyStopEvent:
    def is_set(self):
        return False


class MockONNXSession:
    def __init__(self, output_tensor):
        self.output_tensor = output_tensor

    def get_inputs(self):
        class DummyInput:
            name = "images"
            shape = [1, 3, 640, 640]
        return [DummyInput()]

    def run(self, output_names, input_feed):
        return [self.output_tensor]


def test_area_selection():
    gc = DummyGameConnector()
    auto = PetAutomation(game_connector=gc)

    auto.set_ocr_area((10, 10, 100, 100))
    assert auto.ocr_area == (10, 10, 100, 100)
    assert auto.get_yolo_area() == (10, 10, 100, 100), "Should fallback to ocr_area when yolo_area is not set"

    auto.set_yolo_area((50, 50, 200, 200))
    assert auto.yolo_area == (50, 50, 200, 200)
    assert auto.get_yolo_area() == (50, 50, 200, 200), "Should return yolo_area when explicitly set"
    print("test_area_selection passed.")


def test_detection_modes():
    gc = DummyGameConnector()
    auto = PetAutomation(game_connector=gc)

    auto.set_detection_mode("ocr")
    assert auto.detection_mode == "ocr"

    auto.set_detection_mode("YOLO Only")
    assert auto.detection_mode == "yolo"

    auto.set_detection_mode("OCR + YOLO (Hybrid Mode)")
    assert auto.detection_mode == "hybrid"
    print("test_detection_modes passed.")


def test_or_logic_matching():
    gc = DummyGameConnector()
    auto = PetAutomation(game_connector=gc)
    auto.set_yolo_area((0, 0, 640, 640))
    auto.set_yolo_class_names(["cat", "dog", "rare_pet", "legendary_pet"])

    # Targets selected by user (OR Logic)
    auto.set_yolo_targets(["rare_pet", "legendary_pet"])

    # Output tensor format: End-to-End ONNX NMS (1, N, 6) -> [x1, y1, x2, y2, score, class_id]
    # Here class_id = 2 ("rare_pet") with score 0.95
    mock_output = np.array([[[10.0, 10.0, 50.0, 50.0, 0.95, 2.0]]], dtype=np.float32)
    auto.yolo_session = MockONNXSession(mock_output)

    matched, cname, conf, bbox, cid, *rest = auto._yolo_match_targets()
    assert matched is True
    assert cname == "rare_pet"
    assert abs(conf - 0.95) < 1e-4
    assert cid == 2
    print("test_or_logic_matching passed.")


def test_validate_config():
    gc = DummyGameConnector()
    core = DummyBotCore()
    auto = PetAutomation(game_connector=gc, bot_core=core)

    # Set required coordinates
    for key in auto.coords.keys():
        auto.coords[key] = (10, 10)

    # Mode: YOLO
    auto.set_detection_mode("yolo")
    ok, err = auto._validate_config()
    assert ok is False, "Should fail when model_path is not set"

    auto.set_yolo_model_path("dummy_model.onnx")
    ok, err = auto._validate_config()
    assert ok is False, "Should fail when model file does not exist on disk"
    print("test_validate_config passed.")


if __name__ == "__main__":
    test_area_selection()
    test_detection_modes()
    test_or_logic_matching()
    test_validate_config()
    print("All YOLO unit tests passed successfully!")
