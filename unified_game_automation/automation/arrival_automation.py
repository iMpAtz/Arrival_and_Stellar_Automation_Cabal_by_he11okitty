# Arrival skill automation logic
# Ported from arrival_skill_ocr/automation.py

import time
import re
from tkinter import messagebox
from data.arrival_data import get_offensive_skills, get_defensive_skills, get_base_stat_name, get_base_stat_lookup, get_all_base_stat_names
from core.base_automation import BaseAutomation


class ArrivalAutomation(BaseAutomation):
    def __init__(self, game_connector, ocr_engine, status_callback=None, bot_core=None):
        """Initialize arrival skill automation"""
        super().__init__(game_connector=game_connector, ocr_engine=ocr_engine, bot_core=bot_core, name="Arrival")

        self.apply_button_coords = None
        self.change_button_coords = None
        self.detection_region = None

        # Configuration
        self.area = None
        self.delay_ms = 1000  # Default delay in milliseconds

        # Stat tracking
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        self.target_found_callback = None

    def set_area(self, area):
        """Set the OCR area"""
        self.area = area
        self.detection_region = area

    def set_apply_button(self, coords):
        """Set the apply button coordinates"""
        self.apply_button_coords = coords

    def set_change_button(self, coords):
        """Set the change button coordinates"""
        self.change_button_coords = coords

    def set_delay(self, delay_ms):
        """Set the delay in milliseconds"""
        self.delay_ms = delay_ms

    def set_target_found_callback(self, callback):
        self.target_found_callback = callback

    def start(self, desired_stats=None):
        """Start the arrival automation"""
        # Check if button coordinates are set
        if not self.apply_button_coords or not self.change_button_coords:
            messagebox.showerror("Error", "Please set both Apply and Change button coordinates.")
            return False

        if not self.area:
            messagebox.showwarning("Missing area definition", "Fix area definition first!")
            return False

        # Connect to game if not already connected
        if not self.game_connector.is_connected():
            if not self.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return False

        # Reset counters for new run
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}

        self.update_status("Starting arrival skill automation")

        if self.running:
            return False
        if not super().start():
            return False
        if self.core:
            self.core.start_watchdog(timeout_sec=12.0, check_interval_sec=1.0)
            self.core.register_thread(
                "arrival-automation-loop",
                self.reroll_loop,
                daemon=True,
                args=(desired_stats,),
            )
        return True

    def stop(self):
        """Stop the arrival automation"""
        self.running = False
        if self.core:
            self.core.stop()
        self.update_status("Arrival automation stopped")

        # Show summary of stats if we have any
        if self.stat_counter:
            self.show_stats_summary()

    def emergency_stop(self):
        """Emergency stop the automation"""
        if self.running:
            self.stop()
            self.update_status("🚨 EMERGENCY STOP - Arrival automation stopped!")

    def detect_text_in_image(self, image):
        """Detect text in image using Tesseract and parse for arrival skill format"""
        if image is None:
            return {}

        # Extract text using Tesseract
        raw_text = self.ocr_engine.extract_text(image)

        # Print raw OCR text to console for debugging
        print(f"Raw OCR text: {repr(raw_text)}")

        # Fix OCR misreading + as 4 (only when there's no + sign already)
        cleaned_text = re.sub(r'([A-Za-z\s\.]+)\s4(\d)', r'\1 +\2', raw_text)

        # Fix OCR misreading dots as commas
        from core.observations import normalize_numbers
        cleaned_text = normalize_numbers(cleaned_text)

        # Parse for arrival skill format (dual stats, no "Stellar" text)
        return self.parse_arrival_text(cleaned_text)

    def parse_arrival_text(self, text):
        from core.observations import parse_stats
        observation = parse_stats(text, get_all_base_stat_names())
        for warning in observation.warnings:
            self.unmapped_ocr_counter[warning] = self.unmapped_ocr_counter.get(warning, 0) + 1
        return {stat.name: stat.value for stat in observation.stats}

    def handle_arrival_skill_special_cases(self, text):
        """
        Handle special cases for arrival skills with long names that get truncated
        Returns a dictionary of detected arrival skills with or without values
        """
        special_stats = {}
        lines = (text or "").split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue
            line_lower = line.lower()
            # Case 1: Skill Cool Time decreased - with line-scoped value extraction
            # Look for Skill Cool Time decreased (cut down arrival requirement)
            if ('cool' in line_lower and 'time' in line_lower) or \
               ('skill cool time' in line_lower) or \
               ('cool time decreas' in line_lower):
                # Look for numbers specifically on the cool time line
                value_match = re.search(r'[-+]?\s*(\d+)\s*s?', line_lower)
                if value_match:
                    value = abs(int(value_match.group(1)))  # Use abs() to convert negative to positive
                    special_stats["Skill Cool Time decreased."] = value
                else:
                    special_stats["Skill Cool Time decreased."] = None

            # Case 2: Arrival Skill Buff Time UP / Duration Increase
            elif ('buff' in line_lower and 'time' in line_lower) or \
                 ('duration' in line_lower):
                value_match = re.search(r'[-+]?\s*(\d+)\s*s?', line_lower)
                if value_match:
                    value = abs(int(value_match.group(1)))
                    special_stats["Arrival Skill Buff Time UP"] = value
                else:
                    special_stats["Arrival Skill Buff Time UP"] = None

        return special_stats

    def is_arrival_skill_line(self, line):
        """
        Check if a line contains arrival skill text that should be skipped in normal processing
        """
        line_lower = (line or "").strip().lower()
        return ('cool' in line_lower and 'time' in line_lower) or \
               ('buff' in line_lower and 'time' in line_lower) or \
               ('duration' in line_lower)

    def match_stat_name(self, detected_name):
        """Match detected stat name to known arrival skill stats (O(1) dict lookup with fallback)"""
        detected_normalized = detected_name.lower().replace(' ', '').replace('.', '')

        lookup = get_base_stat_lookup()
        if detected_normalized in lookup:
            return lookup[detected_normalized]

        # Partial match fallback
        for known_stat in get_all_base_stat_names():
            known_lower = known_stat.lower().replace(' ', '').replace('.', '')
            if detected_normalized in known_lower or known_lower in detected_normalized:
                return known_stat

        return None

    def reroll_loop(self, desired_stats):
        from core.fsm import VerifiedReroll
        from core.observations import parse_stats, evaluate
        constraints = [(get_base_stat_name(name), minimum)
                       for group in (desired_stats or {}).values()
                       for name, minimum, _ in group]
        if not constraints:
            self.core.stop("no_targets")
            return

        def observe():
            image = self.game_connector.capture_area_bitblt(self.area)
            self.last_image = image
            raw = self.ocr_engine.extract_text(image, fresh=True) if image is not None else ""
            return parse_stats(raw, get_all_base_stat_names())

        def decide(observation):
            for stat in observation.stats:
                key = f"{stat.name} +{stat.value}"
                self.stat_counter[key] = self.stat_counter.get(key, 0) + 1
            return evaluate(observation, constraints)

        def act():
            if not self.protected_click(self.change_button_coords, "Change"):
                return False
            if not self.safe_sleep_ms(self.delay_ms):
                return False
            return self.protected_click(self.apply_button_coords, "Apply")

        def matched():
            if self.target_found_callback:
                self.target_found_callback()
        VerifiedReroll(self, observe, decide, act, matched, self.delay_ms).run()
        self.running = False

    def check_desired_stats(self, current_stats, desired_stats):
        """
        Check if current stats meet the desired criteria for arrival skills
        - If any stat from the desired list is found with minimum value, return True (OR logic)
        - Stop automation as soon as ANY desired stat is found
        """
        if not desired_stats:
            return True

        if not desired_stats.get('offensive') and not desired_stats.get('defensive'):
            return True

        # Check all offensive stats (if specified)
        if desired_stats.get('offensive'):
            for display_stat_name, min_value, variation in desired_stats['offensive']:
                base_stat_name = get_base_stat_name(display_stat_name)

                if base_stat_name in current_stats:
                    stat_value = current_stats[base_stat_name]
                    if stat_value is None:
                        # Special case: arrival skill detected but value unavailable due to UI collision
                        self.update_status(f"🎉 FOUND: {display_stat_name} detected!")
                        self.update_status("⚠️ Note: Cannot verify value due to UI collision - please check manually")
                        return False
                    elif stat_value >= min_value:
                        self.update_status(f"✅ MATCH: Found {display_stat_name} with value {stat_value} (target: {min_value}+)")
                        return True  # Found one! Stop immediately

        # Check all defensive stats (if specified)
        if desired_stats.get('defensive'):
            for display_stat_name, min_value, variation in desired_stats['defensive']:
                base_stat_name = get_base_stat_name(display_stat_name)

                if base_stat_name in current_stats:
                    stat_value = current_stats[base_stat_name]
                    if stat_value is None:
                        # Special case: arrival skill detected but value unavailable due to UI collision
                        self.update_status(f"🎉 FOUND: {display_stat_name} detected!")
                        self.update_status("⚠️ Note: Cannot verify value due to UI collision - please check manually")
                        return False
                    elif stat_value >= min_value:
                        self.update_status(f"✅ MATCH: Found {display_stat_name} with value {stat_value} (target: {min_value}+)")
                        return True  # Found one! Stop immediately

        return False  # No match found

    def show_stats_summary(self):
        """Show summary of detected stats"""
        self.update_status("")
        self.update_status("SUMMARY OF DETECTED STATS")

        # Separate stats by category
        offensive_base_stats = set(get_base_stat_name(stat) for stat in get_offensive_skills())
        defensive_base_stats = set(get_base_stat_name(stat) for stat in get_defensive_skills())

        # Group stats by category
        offensive_stats = {}
        defensive_stats = {}
        other_stats = {}

        for stat_key, count in self.stat_counter.items():
            # Extract the stat name from the key (format is "stat_name +value")
            parts = stat_key.split("+")
            if len(parts) >= 1:
                stat_name = parts[0].strip()

                # Categorize the stat
                if stat_name in offensive_base_stats:
                    offensive_stats[stat_key] = count
                elif stat_name in defensive_base_stats:
                    defensive_stats[stat_key] = count
                else:
                    other_stats[stat_key] = count

        # Display offensive stats
        if offensive_stats:
            self.update_status("Offensive Stats:")
            for stat_key, count in sorted(offensive_stats.items(), key=lambda x: x[1], reverse=True):
                self.update_status(f"  • {stat_key} × {count}")

        # Display defensive stats
        if defensive_stats:
            self.update_status("Defensive Stats:")
            for stat_key, count in sorted(defensive_stats.items(), key=lambda x: x[1], reverse=True):
                self.update_status(f"  • {stat_key} × {count}")

        # Display other stats
        if other_stats:
            self.update_status("Other Stats:")
            for stat_key, count in sorted(other_stats.items(), key=lambda x: x[1], reverse=True):
                self.update_status(f"  • {stat_key} × {count}")

        # Display unmapped stats (stats detected by OCR but not in our data)
        if self.unmapped_ocr_counter:
            self.update_status("🔍 Unmapped Stats (not in our data):")
            for stat_key, count in sorted(self.unmapped_ocr_counter.items(), key=lambda x: x[1], reverse=True):
                self.update_status(f"  • {stat_key} × {count}")

        self.update_status("📊 Roll statistics summary logged to terminal.")

