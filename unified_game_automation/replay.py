"""Usage: python unified_game_automation/replay.py crop.png --tool Arrival --target Defense --minimum 200"""
import argparse
import json
from PIL import Image
from core.ocr_engine import OCREngine
from core.replay import analyze_image


def main():
    parser = argparse.ArgumentParser(description="Inspect a saved stat crop without sending game input")
    parser.add_argument("image")
    parser.add_argument("--tool", choices=["Arrival", "Stellar"], default="Arrival")
    parser.add_argument("--target", required=True)
    parser.add_argument("--minimum", type=int, default=0)
    args = parser.parse_args()
    with Image.open(args.image) as image:
        result = analyze_image(image.convert("RGB"), args.tool, OCREngine(), [(args.target, args.minimum)])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if result["decision"] == "unknown" else 0


if __name__ == "__main__":
    raise SystemExit(main())
