# Arrival skill automation logic
# Ported from arrival_skill_ocr/automation.py

import time
import re
from tkinter import messagebox
from data.arrival_data import get_offensive_skills, get_defensive_skills, get_base_stat_name
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
        import re
        cleaned_text = re.sub(r'([A-Za-z\s\.]+)\s4(\d)', r'\1 +\2', raw_text)

        # Fix OCR misreading dots as commas
        cleaned_text = cleaned_text.replace(',', '.')

        # Parse for arrival skill format (dual stats, no "Stellar" text)
        return self.parse_arrival_text(cleaned_text)

    def parse_arrival_text(self, text):
        """
        Parse text for arrival skill format
        Expected format: Two stats with values (no "Stellar" text)
        Example:
        Add. Damage        +45
        HP Absorb Up       +2%

        Special handling for long arrival skill names that get cut off:
        - "Arrival Skill Cool time decreas," -> "Arrival Skill Cool Time decreased."
        - "Arrival Skill Duration" -> "Arrival Skill Duration Increase"
        """
        current_stats = {}

        # First, handle special cases for arrival skills with truncated names
        current_stats.update(self.handle_arrival_skill_special_cases(text))

        # Split text into lines for normal processing
        lines = text.strip().split('\n')

        # Look for stat patterns in each line
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip lines that are already handled by special cases
            if self.is_arrival_skill_line(line):
                continue

            # Try to match stat patterns: "Stat Name +Value" or "Stat Name Value"
            # Handle both percentage and numeric values
            patterns = [
                r'(.+?)\s*\+(\d+)%',  # "Stat Name +5%"
                r'(.+?)\s*\+(\d+)',   # "Stat Name +45"
                r'(.+?)\s*(\d+)%',    # "Stat Name 5%"
                r'(.+?)\s*(\d+)',     # "Stat Name 45"
            ]

            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    stat_name = match.group(1).strip()
                    value_str = match.group(2).strip()

                    # Clean up stat name
                    stat_name = stat_name.replace('.', '').strip()

                    # Try to match against known stats
                    matched_stat = self.match_stat_name(stat_name)
                    if matched_stat:
                        try:
                            value = int(value_str)
                            current_stats[matched_stat] = value
                        except ValueError:
                            continue
                    else:
                        # Track unmapped stats for summary
                        if '%' in pattern:
                            value_str += '%'
                        unmapped_key = f"{stat_name} +{value_str}"
                        self.unmapped_ocr_counter[unmapped_key] = self.unmapped_ocr_counter.get(unmapped_key, 0) + 1
                    break

        return current_stats

    def handle_arrival_skill_special_cases(self, text):
        """
        Handle special cases for arrival skills with long names that get truncated
        Returns a dictionary of detected arrival skills with or without values
        """
        special_stats = {}
        text_lower = text.lower()

        # Case 1: Arrival Skill Cool Time decreased - with value extraction
        if ('arrival' in text_lower and 'cool' in text_lower and 'time' in text_lower) or \
           ('arrival skill cool time decreas' in text_lower):
            # Try to extract the numeric value (supports both +15s, -15, 15s, 15 formats)
            # Note: OCR often reads this as "-15" but it should be treated as positive value
            value_match = re.search(r'[-+]?\s*(\d+)\s*s?', text_lower)
            if value_match:
                value = abs(int(value_match.group(1)))  # Use abs() to convert negative to positive
                special_stats["Arrival Skill Cool Time decreased."] = value
            else:
                # If no value found, still mark as detected but with None
                special_stats["Arrival Skill Cool Time decreased."] = None

        # Case 2: Arrival Skill Duration Increase
        elif ('arrival' in text_lower and 'duration' in text_lower) or \
             ('arrival skill duration' in text_lower):
            special_stats["Arrival Skill Duration Increase"] = None

        return special_stats

    def is_arrival_skill_line(self, line):
        """
        Check if a line contains arrival skill text that should be skipped in normal processing
        """
        line_lower = line.lower()
        return ('arrival' in line_lower and ('cool' in line_lower or 'duration' in line_lower))

    def match_stat_name(self, detected_name):
        """Match detected stat name to known arrival skill stats"""
        from data.arrival_data import get_all_base_stat_names

        detected_lower = detected_name.lower().replace(' ', '').replace('.', '')

        # Try exact matches first
        for known_stat in get_all_base_stat_names():
            known_lower = known_stat.lower().replace(' ', '').replace('.', '')
            if detected_lower == known_lower:
                return known_stat

        # Try partial matches
        for known_stat in get_all_base_stat_names():
            known_lower = known_stat.lower().replace(' ', '').replace('.', '')
            if detected_lower in known_lower or known_lower in detected_lower:
                return known_stat

        return None

    def reroll_loop(self, desired_stats):
        """Main reroll loop for arrival skill automation"""
        self.update_status("▶️ Starting arrival skill automation...")
        self.update_status(f"⏱️ Using delay: {self.delay_ms}ms between actions")

        iteration_count = 0

        # Pre-compute stat categories
        offensive_base_stats = set(get_base_stat_name(stat) for stat in get_offensive_skills())
        defensive_base_stats = set(get_base_stat_name(stat) for stat in get_defensive_skills())

        # First click the Change button to remove current option
        self.protected_click(self.change_button_coords, label="Change")
        if not self.safe_sleep_ms(self.delay_ms):
            return

        while self.running:
            if self.stop_event.is_set():
                break
            if self.core:
                self.core.heartbeat("arrival-main-loop")
            iteration_count += 1

            # Click Apply button to apply a new option
            self.protected_click(self.apply_button_coords, label="Apply")
            if not self.safe_sleep_ms(self.delay_ms):
                break  # Wait for game to update

            # Capture screenshot using BitBlt
            screenshot = self.game_connector.capture_area_bitblt(self.area)
            if screenshot is None:
                self.update_status("Failed to capture screen, retrying...")
                if not self.safe_sleep_ms(self.delay_ms):
                    break
                continue

            # Detect text in the screenshot
            current_stats = self.detect_text_in_image(screenshot)

            if current_stats:
                # Track stats for summary
                for stat, value in current_stats.items():
                    stat_key = f"{stat} +{value}"
                    self.stat_counter[stat_key] = self.stat_counter.get(stat_key, 0) + 1

                # Log detected stats
                stat_list = [f"{stat}: {value}" for stat, value in current_stats.items()]
                if stat_list:
                    self.update_status(f"Roll #{iteration_count}: " + " | ".join(stat_list))
            else:
                self.update_status(f"Roll #{iteration_count}: No stats detected")

            # Check if we have desired stats
            if self.check_desired_stats(current_stats, desired_stats):
                self.update_status("🎉🎉🎉 SUCCESS! DESIRED STATS FOUND! 🎉🎉🎉")
                self.stop()
                messagebox.showinfo("Success", "Desired stats found! Automation stopped.")
                break

            # If desired stats not found, click the Change button to reroll
            self.protected_click(self.change_button_coords, label="Change")
            if not self.safe_sleep_ms(self.delay_ms):
                break

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
                        self.update_status(f"⚠️ Note: Cannot verify value due to UI collision - please check manually")
                        self.stop()
                        messagebox.showinfo("Found it!", f"{display_stat_name} detected!\n\nNote: Cannot read value due to UI collision.\nPlease verify the value manually.")
                        return True
                    elif stat_value >= min_value:
                        self.update_status(f"✅ MATCH: Found {display_stat_name} with value {stat_value} (target: {min_value}+)")
                        if self.target_found_callback:
                            self.target_found_callback()
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
                        self.update_status(f"⚠️ Note: Cannot verify value due to UI collision - please check manually")
                        self.stop()
                        messagebox.showinfo("Found it!", f"{display_stat_name} detected!\n\nNote: Cannot read value due to UI collision.\nPlease verify the value manually.")
                        return True
                    elif stat_value >= min_value:
                        self.update_status(f"✅ MATCH: Found {display_stat_name} with value {stat_value} (target: {min_value}+)")
                        if self.target_found_callback:
                            self.target_found_callback()
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

        # Reset counters for next run
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
