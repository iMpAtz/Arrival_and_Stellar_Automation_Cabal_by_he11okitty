# Stellar system automation logic
# Extracted from main.py

import time
import re
import threading
from tkinter import messagebox
from data.stellar_data import get_penetration_exceptions

class StellarAutomation:
    def __init__(self, game_connector, ocr_engine, status_callback=None):
        """Initialize stellar system automation"""
        self.game_connector = game_connector
        self.ocr_engine = ocr_engine
        self.status_callback = status_callback

        # Automation state
        self.running = False
        self.loop_in_progress = False
        self.wrong_read_counter = 0

        # Configuration
        self.area = None
        self.imprint_button_coords = None
        self.option_name = ""
        self.option_min_value = ""
        self.delay_ms = 800  # Simplified - removed ping dependency
        self.effect_delay_ms = 1000  # Default 1 second for visual effect clearing

    def update_status(self, message):
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)

    def set_area(self, area):
        """Set the OCR area"""
        self.area = area

    def set_imprint_button(self, coords):
        """Set the imprint button coordinates"""
        self.imprint_button_coords = coords

    def set_effect_delay(self, delay_ms):
        """Set the visual effect clearing delay in milliseconds"""
        self.effect_delay_ms = delay_ms

    def start(self, option_name, option_min_value=""):
        """Start the stellar automation"""
        if not self.area:
            messagebox.showwarning("Missing area definition", "Fix area definition first!")
            return False

        if not self.imprint_button_coords:
            messagebox.showwarning("Missing button coordinates", "Please set the Imprint button coordinates first!")
            return False

        # Connect to game if not already connected
        if not self.game_connector.is_connected():
            if not self.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return False

        # Process option name and minimum value
        self.option_name = re.sub(r"\s+", "", option_name).lower()
        self.option_min_value = re.sub(r"\s+", "", option_min_value).lower()

        self.update_status(f"Starting stellar automation - option: {option_name}, min value: {option_min_value}")

        self.running = True
        self.wrong_read_counter = 0

        # Start automation in thread
        threading.Thread(target=self._start_automation_loop, daemon=True).start()
        return True

    def _start_automation_loop(self):
        """Start the automation loop with initial delay"""
        time.sleep(3)  # Initial delay
        self.loop_ocr()

    def stop(self):
        """Stop the stellar automation"""
        self.running = False
        self.update_status("Stellar automation stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        if self.running:
            self.stop()
            self.update_status("🚨 EMERGENCY STOP - Stellar automation stopped!")

    @staticmethod
    def numeric_compare(option_min_value_int, text):
        """Compare numbers in text with minimum value"""
        numbers_found = re.findall(r"\d+", text)
        for num_str in numbers_found:
            val = int(num_str)
            if val >= option_min_value_int:
                return True
        return False

    def loop_ocr(self):
        """Main OCR loop - extracted from main.py"""
        if self.loop_in_progress:
            self.update_status("loop_ocr called but loop_in_progress is True - skipping re-entrance.")
            return

        if not self.running:
            return

        self.loop_in_progress = True

        try:
            # Wait for visual effects to appear, then click to close them
            time.sleep(self.effect_delay_ms / 1000.0)

            # Click imprint button (which becomes "close" button) to clear visual effects
            if not self.game_connector.click_at_position(self.imprint_button_coords):
                self.update_status("Close button click failed")

            # Small delay to let effects clear
            time.sleep(0.2)

            # Capture screenshot using BitBlt
            screenshot = self.game_connector.capture_area_bitblt(self.area)
            if screenshot is None:
                self.update_status("BitBlt capture failed")
                self.stop()
                return

            # Extract text using Tesseract
            raw_text = self.ocr_engine.extract_text(screenshot)

            # Print raw OCR text to console for debugging
            print(f"Raw OCR text: {repr(raw_text)}")

            text = self.ocr_engine.parse_stellar_text(raw_text)

            self.update_status(f"OCR text: {text}")
            print(text)  # Debug output

            # Check for exactly one number (stellar format validation)
            numbers_found = self.ocr_engine.find_numbers(text)
            print("wrong_read_counter:", self.wrong_read_counter)

            if len(numbers_found) != 1:
                self.wrong_read_counter += 1
                if self.wrong_read_counter > 2:
                    messagebox.showinfo(
                        "Error",
                        "Found wrong amount of numbers - stopping.\n"
                        "Make sure that you've defined area correctly, please restart application"
                    )
                    self.update_status("More than one (or zero) numbers found in text. Stopping.")
                    self.stop()
                    self.loop_in_progress = False
                    return
                else:
                    self.loop_in_progress = False
                    # Schedule next attempt with longer delay
                    threading.Timer(0.7, self.loop_ocr).start()
                    return

            self.wrong_read_counter = 0

            # Check if option name matches
            found_option_name = False
            if self.option_name:
                if self.option_name in text:
                    if self.option_name == "penetration":
                        # Special handling for penetration exceptions
                        exceptions = get_penetration_exceptions()
                        if any(exc in text for exc in exceptions):
                            self.update_status("Found 'penetration' but ignoring special exception phrase.")
                        else:
                            found_option_name = True
                    else:
                        found_option_name = True

            # Check if minimum value matches
            found_option_min_value = False
            if self.option_min_value:
                if self.option_min_value.isdigit():
                    min_val_int = int(self.option_min_value)
                    found_option_min_value = self.numeric_compare(min_val_int, text)
                else:
                    found_option_min_value = (self.option_min_value in text)

            # Check success conditions
            if found_option_name and self.option_min_value and found_option_min_value:
                messagebox.showinfo("Found it!", "Hopefully that's what you have been looking for")
                self.update_status("Both option and minimum value found - success!")
                self.stop()
            elif found_option_name and not self.option_min_value:
                messagebox.showinfo("Found it!", "Option found, minimum value not specified.")
                self.update_status("Option found - success!")
                self.stop()
            else:
                # Continue automation - click imprint button
                if not self.game_connector.is_connected():
                    if not self.game_connector.connect_to_game():
                        self.update_status("Failed to connect to game for clicking")
                        self.stop()
                        return

                # Double click with delay (as in original)
                if not self.game_connector.click_at_position(self.imprint_button_coords):
                    self.update_status("First click failed")

                time.sleep(0.3)

                if not self.game_connector.click_at_position(self.imprint_button_coords):
                    self.update_status("Second click failed")

                self.loop_in_progress = False
                # Schedule next iteration
                threading.Timer(self.delay_ms / 1000, self.loop_ocr).start()
                return

        except Exception as e:
            self.update_status(f"Error in OCR loop: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
            self.stop()

        self.loop_in_progress = False
