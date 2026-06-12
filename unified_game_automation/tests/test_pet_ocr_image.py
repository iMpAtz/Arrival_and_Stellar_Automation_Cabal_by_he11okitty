import argparse
import sys
from pathlib import Path

import pytesseract
from PIL import Image

try:
    from paddleocr import PaddleOCR
    import numpy as np
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

# Allow importing the project modules when the script is run directly.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.pet_automation import PetAutomation
from core.ocr_engine import OCREngine


class FileGameConnector:
    def __init__(self, image_path):
        self.image_path = Path(image_path)

    def take_screenshot(self, area):
        return Image.open(self.image_path)

    def is_connected(self):
        return True


class PaddleOcrEngine:
    def __init__(self, lang="en"):
        if not PADDLE_AVAILABLE:
            raise RuntimeError("PaddleOCR is not installed")
        self.ocr = PaddleOCR(use_textline_orientation=False, lang=lang)

    def extract_text(self, image):
        if image.mode != "RGB":
            image = image.convert("RGB")
        results = self.ocr.ocr(np.array(image), cls=False)
        text = " ".join([line[-1][0] for line in results])
        return text


def run_image_test(image_path, target, use_paddle=False):
    if use_paddle and not PADDLE_AVAILABLE:
        raise RuntimeError("PaddleOCR is not installed. Install paddleocr to use this mode.")

    if not use_paddle:
        tesseract_path = ROOT / "Tesseract" / "tesseract.exe"
        if tesseract_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)
            sys._MEIPASS = str(ROOT)

    game_connector = FileGameConnector(image_path=image_path)
    ocr_engine = PaddleOcrEngine() if use_paddle else OCREngine(status_callback=lambda msg: print(f"OCR: {msg}"))
    automation = PetAutomation(game_connector=game_connector, ocr_engine=ocr_engine)

    image = Image.open(image_path)
    width, height = image.size
    automation.set_area((0, 0, width, height))

    raw_text = ocr_engine.extract_text(image)
    print("PET OCR IMAGE TEST")
    print(f"  image_path = {image_path}")
    print(f"  ocr_engine = {'PaddleOCR' if use_paddle else 'Tesseract'}")
    print(f"  target     = {target}")
    print(f"  raw_text   = {raw_text!r}")

    automation.set_ocr_search_texts([target])
    matched, normalized = automation._ocr_match_pet_targets()

    print(f"  area       = {automation.area}")
    print(f"  matched    = {matched}")
    print(f"  normalized = {normalized!r}")

    return matched, normalized



def main():
    parser = argparse.ArgumentParser(description="Run pet OCR matching against a screenshot image.")
    parser.add_argument("--image-path", required=True, help="Path to the screenshot image file")
    parser.add_argument("--target", required=True, help="OCR target label to match")
    parser.add_argument("--use-paddle", action="store_true", help="Use PaddleOCR instead of Tesseract")
    args = parser.parse_args()

    run_image_test(args.image_path, args.target, use_paddle=args.use_paddle)


if __name__ == "__main__":
    main()
