import re
from tkinter import messagebox

from core.base_automation import BaseAutomation
from data.stellar_data import get_penetration_exceptions


class StellarAutomation(BaseAutomation):
    def __init__(self, game_connector, ocr_engine, status_callback=None, bot_core=None):
        super().__init__(game_connector=game_connector, ocr_engine=ocr_engine, bot_core=bot_core, name="Stellar")
        self.loop_in_progress = False
        self.wrong_read_counter = 0
        self.area = None
        self.imprint_button_coords = None
        self.option_name = ""
        self.option_min_value = ""
        # Stat tracking
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        self.target_found_callback = None

    def set_area(self, area):
        self.area = area

    def set_imprint_button(self, coords):
        self.imprint_button_coords = coords

    def set_effect_delay(self, delay_ms):
        self.effect_delay_ms = max(0, int(delay_ms))

    def set_target_found_callback(self, callback):
        self.target_found_callback = callback

    def start(self, option_name, option_min_value=""):
        if not self.area:
            messagebox.showwarning("Missing area definition", "Fix area definition first!")
            return False
        if not self.imprint_button_coords:
            messagebox.showwarning("Missing button coordinates", "Please set the Imprint button coordinates first!")
            return False
        if not self.game_connector.is_connected() and not self.game_connector.connect_to_game():
            messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
            return False
        if self.running:
            return False
        if not super().start():
            return False

        self.option_name = re.sub(r"\s+", "", option_name).lower()
        self.option_min_value = re.sub(r"\s+", "", option_min_value).lower()
        self.wrong_read_counter = 0
        
        # Reset counters for new run
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        
        self.update_status(f"Starting stellar automation - option: {option_name}, min value: {option_min_value}")

        self.core.start_watchdog(timeout_sec=12.0, check_interval_sec=1.0)
        self.core.register_thread("stellar-automation-loop", self._automation_loop, daemon=True)
        return True

    def stop(self):
        was_running = self.running
        self.running = False
        if self.core:
            self.core.stop()
        if was_running:
            self.update_status("Stellar automation stopped")

    def emergency_stop(self):
        if self.running:
            self.stop()
            self.update_status("🚨 EMERGENCY STOP - Stellar automation stopped!")

    @staticmethod
    def numeric_compare(option_min_value_int, text):
        numbers_found = re.findall(r"\d+", text)
        return any(int(num_str) >= option_min_value_int for num_str in numbers_found)

    def _automation_loop(self):
        if not self.safe_sleep_ms(3000):
            return
        while self.running and not self.stop_event.is_set():
            if self.core:
                self.core.heartbeat("stellar-main-loop")
            if not self.loop_ocr():
                break
            if not self.safe_sleep_ms(self.delay_ms):
                break
        self.running = False

    def loop_ocr(self):
        if self.loop_in_progress:
            self.update_status("loop_ocr called but loop_in_progress is True - skipping re-entrance.")
            return True
        if not self.running:
            return False

        self.loop_in_progress = True
        try:
            if not self.safe_sleep_ms(self.effect_delay_ms):
                return False
            self.protected_click(self.imprint_button_coords, "Close")
            if not self.safe_sleep_ms(200):
                return False

            screenshot = self.game_connector.capture_area_bitblt(self.area)
            if screenshot is None:
                self.update_status("BitBlt capture failed")
                self.stop()
                return False

            raw_text = self.ocr_engine.extract_text(screenshot)
            text = self.ocr_engine.parse_stellar_text(raw_text)
            text_compact = re.sub(r"\s+", "", text).lower()
            self.update_status(f"OCR text: {text}")

            # Track the full OCR text for unmapped options
            if text.strip():
                text_key = text.strip()[:50]  # Limit length
                self.unmapped_ocr_counter[text_key] = self.unmapped_ocr_counter.get(text_key, 0) + 1

            numbers_found = self.ocr_engine.find_numbers(text)
            if len(numbers_found) != 1:
                self.wrong_read_counter += 1
                if self.wrong_read_counter > 2:
                    messagebox.showinfo(
                        "Error",
                        "Found wrong amount of numbers - stopping.\n"
                        "Make sure that you've defined area correctly, please restart application",
                    )
                    self.update_status("More than one (or zero) numbers found in text. Stopping.")
                    self.stop()
                    return False
                if not self.safe_sleep_ms(700):
                    return False
                return True

            self.wrong_read_counter = 0
            
            # Track the found value
            if numbers_found:
                found_value = numbers_found[0]
                value_key = f"{found_value}"
                self.stat_counter[value_key] = self.stat_counter.get(value_key, 0) + 1
            
            found_option_name = False
            if self.option_name and self.option_name in text_compact:
                if self.option_name == "penetration":
                    exceptions = get_penetration_exceptions()
                    if any(exc in text_compact for exc in exceptions):
                        self.update_status("Found 'penetration' but ignoring special exception phrase.")
                    else:
                        found_option_name = True
                else:
                    found_option_name = True

            found_option_min_value = False
            if self.option_min_value:
                if self.option_min_value.isdigit():
                    found_option_min_value = self.numeric_compare(int(self.option_min_value), text_compact)
                else:
                    found_option_min_value = self.option_min_value in text_compact

            if found_option_name and (not self.option_min_value or found_option_min_value):
                messagebox.showinfo("Found it!", "Target option found.")
                self.update_status("Target option found - success!")
                if self.target_found_callback:
                    self.target_found_callback()
                self.stop()
                return False

            self.protected_click(self.imprint_button_coords, "Imprint")
            if not self.safe_sleep_ms(300):
                return False
            self.protected_click(self.imprint_button_coords, "Imprint")
            return True
        except Exception as e:
            self.update_status(f"Error in OCR loop: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
            self.stop()
            return False
        finally:
            self.loop_in_progress = False