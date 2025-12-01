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

        # Set up Tesseract path (exactly as in main.py)
        # The base_path should be the main script directory, not the core module directory
        import __main__
        if hasattr(__main__, '__file__'):
            main_script_dir = os.path.dirname(os.path.abspath(__main__.__file__))
        else:
            main_script_dir = os.getcwd()

        base_path = getattr(sys, "_MEIPASS", main_script_dir)
        tesseract_path = os.path.join(base_path, "Tesseract", "tesseract.exe")
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

        if status_callback:
            status_callback("Tesseract OCR initialized")

    def update_status(self, message):
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)

    def extract_text(self, image):
        """
        Extract text from image using Tesseract
        Args:
            image: PIL Image object
        Returns:
            Raw text string from OCR
        """
        try:
            if image is None:
                return ""

            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            self.update_status(f"OCR error: {str(e)}")
            return ""

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
        Expected format: Two stats with values (no "Stellar" text)
        """
        # TODO: Implement arrival skill text parsing
        # This will need to detect two stats and their values
        return {}

    def find_numbers(self, text):
        """Find all numbers in text"""
        return re.findall(r"\d+", text)
