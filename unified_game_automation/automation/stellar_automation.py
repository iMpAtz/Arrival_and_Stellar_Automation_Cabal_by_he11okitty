import re
from tkinter import messagebox

from core.base_automation import BaseAutomation
from data.stellar_data import get_penetration_exceptions


class StellarAutomation(BaseAutomation):
    # Timing constants (ms)
    INITIAL_LOOP_DELAY_MS = 3000
    IMPRINT_POST_CLICK_DELAY_MS = 200
    RETRY_READ_DELAY_MS = 700
    IMPRINT_DOUBLE_CLICK_DELAY_MS = 300

    def __init__(self, game_connector, ocr_engine, status_callback=None, bot_core=None):
        super().__init__(game_connector=game_connector, ocr_engine=ocr_engine, bot_core=bot_core, name="Stellar")
        self.loop_in_progress = False
        self.wrong_read_counter = 0
        self.area = None
        self.imprint_button_coords = None
        self.option_constraints = []
        self.effect_delay_ms = 1000
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

    def start(self, option_constraints):
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

        if isinstance(option_constraints, str):
            option_constraints = [{'name': option_constraints, 'min_value': ''}]
        elif isinstance(option_constraints, tuple):
            option_constraints = [{'name': option_constraints[0], 'min_value': option_constraints[1] if len(option_constraints) > 1 else ''}]

        parsed_constraints = []
        for constraint in option_constraints:
            if isinstance(constraint, dict):
                name = constraint.get('name', '')
                min_value = constraint.get('min_value', '')
            elif isinstance(constraint, (list, tuple)):
                name = constraint[0] if len(constraint) > 0 else ''
                min_value = constraint[1] if len(constraint) > 1 else ''
            else:
                name = str(constraint)
                min_value = ''

            name_normalized = re.sub(r"\s+", "", name).lower()
            min_normalized = re.sub(r"\s+", "", str(min_value)).lower()
            if name_normalized:
                parsed_constraints.append({
                    'name': name_normalized,
                    'min_value': min_normalized,
                    'display_name': name.strip()
                })

        self.option_constraints = parsed_constraints
        self.wrong_read_counter = 0
        
        # Reset counters for new run
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        
        display_options = ", ".join([c.get('display_name', c['name']) for c in self.option_constraints]) if self.option_constraints else ""
        self.update_status(f"Starting stellar automation - options: {display_options}")

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

    def min_value_matches(self, min_value, text):
        if not min_value:
            return True
        if min_value.isdigit():
            return self.numeric_compare(int(min_value), text)
        return min_value in text

    def _automation_loop(self):
        from core.fsm import VerifiedReroll
        from core.observations import parse_stats, evaluate
        from data.stellar_data import get_stellar_options
        constraints = []
        for constraint in self.option_constraints:
            value = str(constraint.get("min_value", "")).strip().lstrip("+").rstrip("%")
            if value and not value.isdigit():
                self.core.stop("invalid_minimum")
                return
            constraints.append((constraint["display_name"], int(value or 0)))
        if not constraints:
            self.core.stop("no_targets")
            return

        def observe():
            image = self.game_connector.capture_area_bitblt(self.area)
            self.last_image = image
            raw = self.ocr_engine.extract_text(image, fresh=True) if image is not None else ""
            return parse_stats(raw, get_stellar_options(), stellar=True)

        def decide(observation):
            for stat in observation.stats:
                key = str(stat.value)
                self.stat_counter[key] = self.stat_counter.get(key, 0) + 1
            return evaluate(observation, constraints)

        def act():
            if not self.protected_click(self.imprint_button_coords, "Imprint"):
                return False
            if not self.safe_sleep_ms(self.IMPRINT_DOUBLE_CLICK_DELAY_MS):
                return False
            if not self.protected_click(self.imprint_button_coords, "Confirm imprint"):
                return False
            if not self.safe_sleep_ms(self.effect_delay_ms):
                return False
            return self.protected_click(self.imprint_button_coords, "Close result effect")

        def matched():
            if self.target_found_callback:
                self.target_found_callback()
        VerifiedReroll(self, observe, decide, act, matched, self.delay_ms).run()
        self.running = False
