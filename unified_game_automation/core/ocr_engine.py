# Tesseract OCR engine wrapper
# Replaces PaddleOCR functionality from arrival_skill_ocr

import pytesseract
from PIL import Image
import re
import os
import sys

class OCREngine:
    def __init__(self, status_callback=None):
        """Initialize the Tesseract OCR engine"""
        self.status_callback = status_callback

        from core.paths import resource_root
        import threading
        from collections import OrderedDict
        tesseract_dir = resource_root() / "Tesseract"
        self.tessdata_dir = str(tesseract_dir / "tessdata").replace("\\", "/")
        os.environ["TESSDATA_PREFIX"] = self.tessdata_dir
        self.tesseract_path = str(tesseract_dir / "tesseract.exe")
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        self.timeout_seconds = 4.0
        self.cache_ttl = 0.75
        self._cache = OrderedDict()
        self._cache_lock = threading.RLock()
        self._local = threading.local()
        self.metrics = {"calls": 0, "cache_hits": 0, "seconds": 0.0}

    @property
    def last_error(self):
        return getattr(self._local, "error", "")

    def invalidate_cache(self):
        with self._cache_lock:
            self._cache.clear()

    def diagnostics(self):
        return {"tesseract": os.path.isfile(self.tesseract_path),
                "english_data": os.path.isfile(os.path.join(self.tessdata_dir, "eng.traineddata")),
                "path": self.tesseract_path, "timeout_seconds": self.timeout_seconds}

    def update_status(self, message):
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)

    def _ensure_pil_image(self, image):
        """Ensure input image is a PIL Image object (converts numpy arrays if needed)"""
        if image is None:
            return None
        if not isinstance(image, Image.Image):
            try:
                import numpy as np
                if isinstance(image, np.ndarray):
                    if image.ndim == 3 and image.shape[2] == 3:
                        image = Image.fromarray(np.uint8(image)).convert('RGB')
                    elif image.ndim == 2:
                        image = Image.fromarray(np.uint8(image)).convert('L')
                    else:
                        image = Image.fromarray(np.uint8(image))
            except ImportError:
                pass
        return image

    def extract_text(self, image, config=None, fresh=False):
        import hashlib
        import time
        self._local.error = ""
        try:
            image = self._ensure_pil_image(image)
            if image is None:
                self._local.error = "No image"
                return ""
            # pytesseract uses shlex(posix=False) on Windows, preserving quotes
            # inside argv. Use TESSDATA_PREFIX instead of a split config path.
            tess_config = config or ""
            key = (image.size, image.mode, tess_config,
                   hashlib.blake2b(image.tobytes(), digest_size=16).digest())
            with self._cache_lock:
                now = time.monotonic()
                cached = self._cache.get(key)
                if not fresh and cached and now-cached[0] < self.cache_ttl:
                    self.metrics["cache_hits"] += 1
                    return cached[1]
                started = time.monotonic()
                self.metrics["calls"] += 1
                try:
                    text = pytesseract.image_to_string(image, config=tess_config, timeout=self.timeout_seconds)
                finally:
                    self.metrics["seconds"] += time.monotonic()-started
                if text.strip():
                    self._cache[key] = (time.monotonic(), text)
                    self._cache.move_to_end(key)
                    while len(self._cache) > 32:
                        self._cache.popitem(last=False)
                return text
        except Exception as exc:
            self._local.error = str(exc)
            self.update_status(f"OCR error: {exc}")
            return ""

    def extract_pet_text(self, image):
        """Read the small pet stat region as a text block, not a full page."""
        image = self._ensure_pil_image(image)
        if isinstance(image, Image.Image):
            image = image.resize(
                (image.width * 3, image.height * 3), Image.Resampling.LANCZOS
            )
        return self.extract_text(image, config="--psm 6 --oem 1", fresh=True)

    def extract_pet_reading(self, image):
        """Fresh EP39 text and word confidence from the same Tesseract pass."""
        import time
        self._local.error = ""
        try:
            image = self._ensure_pil_image(image)
            if image is None:
                self._local.error = "No image"
                return "", ()
            image = image.resize((image.width * 3, image.height * 3), Image.Resampling.LANCZOS)
            with self._cache_lock:
                started = time.monotonic()
                self.metrics["calls"] += 1
                try:
                    data = pytesseract.image_to_data(
                        image, config="--psm 6 --oem 1", output_type=pytesseract.Output.DICT,
                        timeout=self.timeout_seconds,
                    )
                finally:
                    self.metrics["seconds"] += time.monotonic() - started
            lines, words = {}, []
            for index, token in enumerate(data["text"]):
                token = token.strip()
                if not token:
                    continue
                line = tuple(data[key][index] for key in ("page_num", "block_num", "par_num", "line_num"))
                lines.setdefault(line, []).append(token)
                words.append((token, float(data["conf"][index])))
            return "\n".join(" ".join(tokens) for tokens in lines.values()), tuple(words)
        except Exception as exc:
            self._local.error = str(exc)
            self.update_status(f"OCR error: {exc}")
            return "", ()

    def extract_numbers(self, image):
        from PIL import ImageEnhance, ImageFilter
        image = self._ensure_pil_image(image)
        if image is None:
            return ""
        image = ImageEnhance.Contrast(image.convert('L')).enhance(2.0).filter(ImageFilter.SHARPEN)
        return self.extract_text(image, '--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789/')

    def parse_stellar_text(self, text):
        """
        Parse text for stellar system format
        Expected format: "Stellar" and "Stellar Force" with option name and value
        """
        # Clean up text (same as main.py)
        text = re.sub(r"\s+", "", text).lower()
        text = re.sub(r'([A-Za-z]+)4(\d)', r'\1+\2', text)

        if "stellarforce4" in text:
            text = text.replace("stellarforce4", "stellarforce+")

        return text

    def parse_arrival_text(self, text):
        """
        Parse text for arrival skill format
        Expected format: Two stats with values
        """
        if not text:
            return {}
        cleaned_text = re.sub(r'([A-Za-z\s\.]+)\s4(\d)', r'\1 +\2', text)
        cleaned_text = cleaned_text.replace(',', '.')
        lines = cleaned_text.strip().split('\n')
        parsed = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = re.search(r'(.+?)\s*[\+]?\s*(\d+)', line)
            if match:
                stat_name = match.group(1).replace('.', '').strip()
                try:
                    val = int(match.group(2))
                    parsed[stat_name] = val
                except ValueError:
                    pass
        return parsed

    def find_numbers(self, text):
        """Find all numbers in text"""
        return re.findall(r"\d+", text)

