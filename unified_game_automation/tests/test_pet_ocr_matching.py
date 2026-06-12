import argparse
import sys
from pathlib import Path

from PIL import Image

# Ensure the project package can be imported when running the test script directly.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.pet_automation import PetAutomation
from core.ocr_engine import OCREngine


class DummyGameConnector:
    def __init__(self, text_to_return):
        self.text_to_return = text_to_return

    def take_screenshot(self, area):
        return self.text_to_return


class FileGameConnector:
    def __init__(self, image_path):
        self.image_path = Path(image_path)

    def take_screenshot(self, area):
        return Image.open(self.image_path)


class DummyOcrEngine:
    def __init__(self, extracted_text):
        self.extracted_text = extracted_text

    def extract_text(self, image):
        return self.extracted_text


def run_test(description, target, ocr_engine, game_connector, expected_match):
    automation = PetAutomation(game_connector=game_connector, ocr_engine=ocr_engine)
    automation.set_area((0, 0, 100, 100))
    automation.set_ocr_search_texts([target])

    matched, normalized = automation._ocr_match_pet_targets()
    print(f"{description}")
    print(f"  target        = {target}")
    print(f"  normalized    = {normalized!r}")
    print(f"  matched       = {matched}")
    print(f"  expected      = {expected_match}\n")
    assert matched == expected_match, f"Expected {expected_match} but got {matched}"


def built_in_tests():
    run_test(
        "Match Ignore Resist Critical Damage when truncated at the start",
        target="Ignore Resist Critical Damage",
        ocr_engine=DummyOcrEngine(extracted_text="nore Resist Critical Damage +8%"),
        game_connector=DummyGameConnector(text_to_return="dummy-screenshot"),
        expected_match=True,
    )

    run_test(
        "Match Ignore Resist Critical Damage when OCR misreads prefix as bnor",
        target="Ignore Resist Critical Damage",
        ocr_engine=DummyOcrEngine(extracted_text="bnor Resist Critical Damage +8%"),
        game_connector=DummyGameConnector(text_to_return="dummy-screenshot"),
        expected_match=True,
    )

    run_test(
        "Do not match Resist Critical Damage when OCR contains Ignore Resist Critical Damage",
        target="Resist Critical Damage",
        ocr_engine=DummyOcrEngine(extracted_text="Ignore Resist Critical Damage +8%"),
        game_connector=DummyGameConnector(text_to_return="dummy-screenshot"),
        expected_match=False,
    )

    run_test(
        "Match Resist Critical Damage when OCR text is exact",
        target="Resist Critical Damage",
        ocr_engine=DummyOcrEngine(extracted_text="Resist Critical Damage +8%"),
        game_connector=DummyGameConnector(text_to_return="dummy-screenshot"),
        expected_match=True,
    )

    run_test(
        "Match Ignore Resist Critical Rate when prefix is truncated",
        target="Ignore Resist Critical Rate",
        ocr_engine=DummyOcrEngine(extracted_text="gnore Resist Critical Rate +2%"),
        game_connector=DummyGameConnector(text_to_return="dummy-screenshot"),
        expected_match=True,
    )

    print("All built-in tests passed.")


def run_image_test(image_path, target):
    game_connector = FileGameConnector(image_path=image_path)
    ocr_engine = OCREngine()
    automation = PetAutomation(game_connector=game_connector, ocr_engine=ocr_engine)
    automation.set_area((0, 0, 100, 100))
    automation.set_ocr_search_texts([target])

    matched, normalized = automation._ocr_match_pet_targets()
    print("Image test result")
    print(f"  target     = {target}")
    print(f"  image_path = {image_path}")
    print(f"  normalized = {normalized!r}")
    print(f"  matched    = {matched}")


def parse_args():
    parser = argparse.ArgumentParser(description="PET OCR matching test script")
    parser.add_argument("--image-path", help="Path to a screenshot image file for OCR testing")
    parser.add_argument("--target", help="OCR target label to test", default="Ignore Resist Critical Damage")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.image_path:
        run_image_test(args.image_path, args.target)
    else:
        built_in_tests()


if __name__ == "__main__":
    main()
