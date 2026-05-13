import time

from core.base_automation import BaseAutomation


class PetAutomation(BaseAutomation):
    def __init__(self, game_connector, ocr_engine, bot_core=None, on_target_found=None):
        super().__init__(
            game_connector=game_connector,
            ocr_engine=ocr_engine,
            bot_core=bot_core,
            name="Pet",
        )
        self.on_target_found = on_target_found
        self.area = None
        self.targets = []
        self.coords = {
            "pet_training": None,
            "untrain_icon": None,
            "wrong_slot": None,
            "untrain_btn": None,
            "yes_btn": None,
        }
        # Stat tracking
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        self._thread_name = "pet-automation-loop"

    def set_area(self, area):
        self.area = area

    def set_ocr_search_texts(self, targets):
        # Store normalized lowercase targets once to avoid inconsistent matching.
        self.targets = [
            self.normalize_text(target)
            for target in (targets or [])
            if self.normalize_text(target)
        ]

    def set_pet_training_coords(self, coords):
        self.coords["pet_training"] = coords

    def set_untrain_pet_icon_coords(self, coords):
        self.coords["untrain_icon"] = coords

    def set_wrong_slot_coords(self, coords):
        self.coords["wrong_slot"] = coords

    def set_untrain_button_coords(self, coords):
        self.coords["untrain_btn"] = coords

    def set_yes_button_coords(self, coords):
        self.coords["yes_btn"] = coords

    def _validate_config(self):
        if not self.core:
            return False, "BotCore is not available"
        missing = [name for name, value in self.coords.items() if not value]
        if missing:
            return False, f"Missing coordinates: {', '.join(missing)}"
        if not self.area:
            return False, "OCR area not set"
        if not self.targets:
            return False, "No OCR targets selected"
        return True, ""

    def start(self):
        is_ok, message = self._validate_config()
        if not is_ok:
            self.update_status(message)
            return False
        if self.running:
            self.update_status("Already running")
            return False
        if not super().start():
            return False
        self.update_status("Automation started")
        
        # Reset counters for new run
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        
        self.core.start_watchdog(timeout_sec=10.0, check_interval_sec=1.0)
        self.core.register_thread(self._thread_name, self._run_loop, daemon=True)
        return True

    def stop(self):
        was_running = self.running
        self.running = False
        if self.core:
            self.core.stop()
            self.core.end_run(tool_name="Pet Untrain")
        if was_running:
            self.update_status("Automation stopped")

    def emergency_stop(self):
        self.running = False
        if self.core:
            self.core.emergency_stop()
            self.core.end_run(tool_name="Pet Untrain")
        self.update_status("EMERGENCY STOP")

    def _run_loop(self):
        steps = [
            ("pet_training", "Pet Training"),
            ("untrain_icon", "Untrain Icon"),
            ("wrong_slot", "Wrong Slot"),
            ("untrain_btn", "Untrain"),
            ("yes_btn", "Yes"),
        ]

        def one_cycle():
            if not self.running or self.stop_event.is_set():
                return False

            if self._check_ocr_and_stop():
                return False

            for key, label in steps:
                if not self.running or self.stop_event.is_set():
                    return False
                if self._check_ocr_and_stop():
                    return False
                if not self.protected_click(self.coords.get(key), label):
                    self.update_status(f"Failed to click {label}")
                    return False
                if not self.safe_sleep_ms(self.delay_ms):
                    return False
                if self._check_ocr_and_stop():
                    return False
            return True

        try:
            self.safe_loop("pet-main-loop", one_cycle)
        finally:
            self.running = False

    def _ocr_match_pet_targets(self):
        """
        Pet-specific OCR matcher.
        Keeps 'Penetration' separate from 'Ignore Penetration':
        - selecting only 'Penetration' must not match 'Ignore Penetration'
        """
        if not self.ocr_engine or not self.area or not self.targets:
            return False, ""
        screenshot = self.game_connector.take_screenshot(self.area)
        if screenshot is None:
            return False, ""

        raw = self.ocr_engine.extract_text(screenshot)
        # OCR text is always normalized/lowercased before comparison.
        normalized = self.normalize_text(raw)
        now = time.time()

        # Track all OCR results
        if normalized.strip():
            text_key = normalized.strip()[:80]  # Limit length
            self.unmapped_ocr_counter[text_key] = self.unmapped_ocr_counter.get(text_key, 0) + 1

        for target in self.targets:
            # Targets are pre-normalized in set_ocr_search_texts.
            target_norm = target
            if not target_norm:
                continue

            # Special case requested by user:
            # 'penetration' should not trigger when OCR reads 'ignore penetration'.
            if target_norm == "penetration":
                if "ignore penetration" in normalized:
                    continue
                if "penetration" in normalized:
                    if now - self._last_ocr_hit_at < self._ocr_debounce_sec:
                        return False, normalized
                    self._last_ocr_hit_at = now
                    return True, normalized
                continue

            if target_norm in normalized:
                if now - self._last_ocr_hit_at < self._ocr_debounce_sec:
                    return False, normalized
                self._last_ocr_hit_at = now
                return True, normalized

        return False, normalized

    def _check_ocr_and_stop(self):
        matched, normalized = self._ocr_match_pet_targets()
        if matched:
            self.update_status(f"OCR target matched: {normalized[:80]}")
            if self.on_target_found:
                try:
                    self.on_target_found(normalized)
                except Exception:
                    pass
            self.stop()
            return True
        return False