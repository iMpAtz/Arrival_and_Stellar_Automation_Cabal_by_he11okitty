import re

from core.base_automation import BaseAutomation


class PetAutomation(BaseAutomation):
    """OCR-based Pet Untrain workflows for Standard and EP39."""

    def __init__(self, game_connector, ocr_engine=None, status_callback=None, bot_core=None, on_target_found=None, on_needs_review=None):
        if status_callback is not None and hasattr(status_callback, 'stop_event'):
            if bot_core is not None and on_target_found is None:
                on_target_found = bot_core
            bot_core = status_callback
            status_callback = None

        super().__init__(
            game_connector=game_connector,
            ocr_engine=ocr_engine,
            bot_core=bot_core,
            name="Pet",
        )
        self.status_callback = status_callback
        self.on_target_found = on_target_found
        self.on_needs_review = on_needs_review
        
        # Detection ROI Areas
        self.area = None          # Legacy / default area
        self.ocr_area = None      # ROI specifically for OCR
        self.targets = []
        self._selected_ocr_targets = []

        self.workflow_mode = "standard"

        # Step coordinates for click sequence
        self.coords = {
            "pet_training": None,
            "untrain_icon": None,
            "wrong_slot": None,
            "untrain_btn": None,
            "yes_btn": None,
            "ep39_click_1": None,
            "ep39_click_2": None,
            "ep39_click_3": None,
        }

        # Stat tracking & debouncing
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        self._thread_name = "pet-automation-loop"

    # -------------------------------------------------------------------------
    # 1. การกำหนดพื้นที่ตรวจจับ (ROI Area Selection)
    # -------------------------------------------------------------------------

    def set_area(self, area):
        """กำหนดพื้นที่เป้าหมายหลัก (Legacy) และตั้งค่า ocr_area เป็นค่าเริ่มต้น"""
        self.area = area
        self.ocr_area = area

    def set_ocr_area(self, area):
        """กำหนดขอบเขตพื้นที่ ROI สำหรับการตรวจจับข้อความด้วย OCR โดยเฉพาะ"""
        self.ocr_area = area
        self.area = area

    def set_ocr_search_texts(self, targets):
        """จัดเตรียมและคัดกรองคำค้นหา OCR (คำยาวมาก่อนคำสั้นเพื่อความแม่นยำ)"""
        self._selected_ocr_targets = list(targets or [])
        normalized_targets = []
        for target in (targets or []):
            normalized = self.normalize_text(target)
            if not normalized or normalized in normalized_targets:
                continue
            normalized_targets.append(normalized)
            words = normalized.split()
            if len(words) > 3:
                fallback = " ".join(words[:-1])
                if fallback and fallback not in normalized_targets:
                    normalized_targets.append(fallback)

        self.targets = sorted(normalized_targets, key=lambda s: (-len(s), s))

    def set_ocr_targets(self, targets):
        self.set_ocr_search_texts(targets)


    # -------------------------------------------------------------------------
    # พิกัดสำหรับขั้นตอนการทำงาน (Step Coordinates)
    # -------------------------------------------------------------------------

    def set_workflow_mode(self, mode):
        if self.running:
            return False
        if mode not in ("standard", "ep39"):
            raise ValueError(f"Unknown pet workflow: {mode}")
        self.workflow_mode = mode
        return True

    def get_step_keys(self):
        if self.workflow_mode == "ep39":
            return ("ep39_click_1", "ep39_click_2", "ep39_click_3")
        return ("pet_training", "untrain_icon", "wrong_slot", "untrain_btn", "yes_btn")


    def set_step_coords(self, step_name, coords):
        step_map = {
            "EP39 Click 1": "ep39_click_1",
            "EP39 Click 2": "ep39_click_2",
            "EP39 Click 3": "ep39_click_3",
            "Pet training": "pet_training",
            "Click on untrain pet icon": "untrain_icon",
            "Click on wrong slot": "wrong_slot",
            "Click untrain button": "untrain_btn",
            "Click yes button": "yes_btn",
        }
        key = step_map.get(step_name, step_name)
        if key in self.coords:
            self.coords[key] = coords

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

    # -------------------------------------------------------------------------
    # 5. การตรวจสอบความพร้อมก่อนเริ่มทำงาน (_validate_config)
    # -------------------------------------------------------------------------

    def _validate_config(self):
        if not self.core:
            return False, "BotCore is not available"
        missing = [name for name in self.get_step_keys() if not self.coords[name]]
        if missing:
            return False, f"Missing coordinates: {', '.join(missing)}"
        if not self.ocr_area and not self.area:
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
        self.update_status(f"Automation started (Workflow: {self.workflow_mode.upper()}, Detection: OCR)")
        
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

    # -------------------------------------------------------------------------
    # Loop การทำงานหลัก
    # -------------------------------------------------------------------------

    def _run_loop(self):
        def gate():
            for attempt in range(3):
                self.core.transition("observe", f"Pet detection {attempt+1}/3")
                if self._check_detection_and_stop() or self.stop_event.is_set():
                    return False
                if self._last_detection_valid:
                    return True
                self.update_status(
                    f"OCR retry {attempt+1}/3: "
                    f"{getattr(self, '_last_ocr_issue', '') or 'Target was not confirmed'}; "
                    f"read={getattr(self, '_last_ocr_raw', '')!r}"
                )
                if not self.safe_sleep_ms(350):
                    return False
            self.update_status("Detection could not confirm the current stat; stopped before clicking.")
            self.core.stop("needs_review")
            return False
        try:
            if self.workflow_mode == "ep39":
                self._run_ep39_loop()
                return
            while self.running and not self.stop_event.is_set():
                for key in self.get_step_keys():
                    if not gate():
                        return
                    self.core.transition("act", key)
                    if not self.protected_click(self.coords[key], key):
                        self.core.stop("action_failed")
                        return
                    if not self.safe_sleep_ms(self.delay_ms):
                        return
                if self.core.session.dry_run:
                    self.core.stop("dry_run_complete")
                    return
        finally:
            self.running = False

    def _ep39_click(self, key):
        if not self.running or self.stop_event.is_set():
            return False
        self.core.transition("act", key)
        if not self.protected_click(self.coords[key], key):
            if not self.stop_event.is_set():
                self.core.stop("action_failed")
            return False
        return True

    def _ep39_popup_decision(self):
        """Read at most three times; a target needs two consecutive equal reads."""
        previous_target = None
        target_seen = False
        for attempt in range(3):
            if not self.running or self.stop_event.is_set():
                return None, ""
            self.core.transition("observe", f"EP39 popup OCR {attempt+1}/3")
            matched, text = self._ocr_match_pet_targets()
            if self.stop_event.is_set():
                return None, ""
            if self._last_ocr_valid:
                if matched:
                    target_seen = True
                    if previous_target == text:
                        return "cancel", text
                    previous_target = text
                    self._last_ocr_issue = "Target needs a second matching OCR read"
                elif not target_seen:
                    return "ok", text
                else:
                    # A conflicting confirmation must not authorize a reroll.
                    previous_target = None
                    self._last_ocr_issue = "OCR changed during target confirmation"
            else:
                previous_target = None
            self.update_status(
                f"OCR retry {attempt+1}/3: {self._last_ocr_issue}; "
                f"read={self._last_ocr_raw!r}"
            )
            if attempt < 2 and not self.safe_sleep_ms(350):
                return None, ""
        return "review", self._last_ocr_raw

    def _ep39_text_is_readable(self, raw, words):
        """Heuristic quality gate, independent of membership in the stat catalog.

        Confidence is not a dictionary or a guarantee of correct spelling.
        Reject obvious fragments/noise while allowing new stat names.
        """
        from data.pet_data import get_pet_ocr_options
        if not re.search(r"[A-Za-z]", raw):
            return False
        if re.search(r"[^A-Za-z0-9\s.,%+\-()/']", raw):
            return False
        if any(conf < 65 for word, conf in words
               if re.search(r"[A-Za-z]", word)
               and not re.fullmatch(r"\d+(?:[.,]\d+)?s", word, re.I)):
            return False
        vocabulary = set(re.findall(r"[a-z]+", " ".join(get_pet_ocr_options()).lower()))
        vocabulary.update({"hp", "mp", "sp", "exp", "pve", "pvp", "ep"})
        # Remove a trailing stat value and its common game units before
        # checking words. In particular, `2s` is a duration, not the word `s`.
        quality_text = "\n".join(
            re.sub(r"\s*[+-]?\s*\d+(?:[.,]\d+)?\s*(?:%|s)?\s*$", "", line, flags=re.I)
            for line in raw.splitlines()
        )
        for token in re.findall(r"[A-Za-z0-9]+", quality_text):
            if token.isdigit():
                continue
            word = token.lower()
            if word in vocabulary or re.fullmatch(r"ep\d+", word):
                continue
            if (not word.isalpha() or len(word) < 2 or len(word) > 24
                    or not re.search(r"[aeiouy]", word)
                    or re.search(r"(.)\1\1", word)
                    or re.search(r"[bcdfghjklmnpqrstvwxz]{5}", word)):
                return False
        return True

    def _run_ep39_loop(self):
        while self.running and not self.stop_event.is_set():
            if not self._ep39_click("ep39_click_1"):
                return
            if not self.safe_sleep_ms(self.delay_ms):
                return
            decision, text = self._ep39_popup_decision()
            if decision is None or self.stop_event.is_set():
                return
            if decision == "review":
                issue = self._last_ocr_issue
                self.update_status("EP39 OCR unclear; game popup left open for review.")
                self.core.stop("needs_review")
                if self.on_needs_review:
                    self.on_needs_review(issue, text)
                return
            if decision == "cancel":
                # Cancel must be dispatched while input is still authorized.
                if not self._ep39_click("ep39_click_3"):
                    return
                self.core.stop("target_found")
                if self.on_target_found:
                    self.on_target_found("ocr", text)
                return
            if not self._ep39_click("ep39_click_2"):
                return
            if not self.safe_sleep_ms(self.delay_ms):
                return
            if self.core.session.dry_run:
                self.core.stop("dry_run_complete")
                return

    def _ocr_contains_ignore_variants(self, normalized, suffix):
        if not suffix:
            return False
        return any(
            variant in normalized
            for variant in [
                f"ignore {suffix}",
                f"nore {suffix}",
                f"gnore {suffix}",
                f"bnor {suffix}",
                f"nor {suffix}",
            ]
        )

    @staticmethod
    def _normalize_ep39_text(text):
        """Ignore numeric stat values while retaining the meaningful `2s` unit."""
        text = re.sub(r"(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])", " ", text or "")
        return PetAutomation.normalize_text(text)

    def _ocr_match_pet_targets(self, require_targets=True):
        from core.observations import normalize_name
        from data.pet_data import get_pet_ocr_options
        self._last_ocr_valid = False
        self._last_ocr_raw = ""
        self._last_ocr_issue = ""
        target_area = self.ocr_area or self.area
        if not self.ocr_engine or not target_area:
            self._last_ocr_issue = "Missing OCR engine or area"
            return False, ""
        if require_targets and not self.targets:
            self._last_ocr_issue = "No OCR targets selected"
            return False, ""
        screenshot = self.game_connector.take_screenshot(target_area)
        if screenshot is None:
            self._last_ocr_issue = "Could not capture the OCR area"
            return False, ""
        # Keep compatibility with injected OCR engines used by replay/tests.
        if hasattr(self.ocr_engine, "invalidate_cache"):
            self.ocr_engine.invalidate_cache()
        words = ()
        if self.workflow_mode == "ep39" and callable(getattr(type(self.ocr_engine), "extract_pet_reading", None)):
            raw, words = self.ocr_engine.extract_pet_reading(screenshot)
        elif callable(getattr(type(self.ocr_engine), "extract_pet_text", None)):
            raw = self.ocr_engine.extract_pet_text(screenshot)
        else:
            raw = self.ocr_engine.extract_text(screenshot)
        raw = raw or ""
        self._last_ocr_raw = raw
        strict = self.workflow_mode == "ep39"
        normalized = (self._normalize_ep39_text(raw) if strict
                      else self.normalize_text(raw))
        if not raw.strip():
            error = getattr(self.ocr_engine, "last_error", "")
            self._last_ocr_issue = error if isinstance(error, str) and error else "OCR returned no text"
            return False, normalized
        strict = self.workflow_mode == "ep39"
        name_key = self._normalize_ep39_text if strict else normalize_name
        catalog = {name_key(name): name for name in get_pet_ocr_options()}
        selected = {name_key(target) for target in
                    (self._selected_ocr_targets if strict else self.targets)}
        lines = [line.strip() for line in raw.splitlines() if line.strip()]

        def key_for(text):
            if strict:
                # Stat values do not affect name matching; `_normalize_ep39_text`
                # preserves the special duration token `2s` and strips other numbers.
                return name_key(text)
            text = re.sub(r"^(?:nore|gnore|bnor|nor)\s+", "ignore ", text, flags=re.I)
            return normalize_name(text)

        detected, unknown = [], []
        index = 0
        while index < len(lines):
            # A narrow ROI may wrap one stat across several OCR lines.
            # Match full names only, preserving Ignore/Cancel Ignore distinctions.
            for count in range(1, min(3, len(lines) - index) + 1):
                candidate = " ".join(lines[index:index + count])
                if strict:
                    # `2s` remains visible in normalized OCR, but is a value
                    # suffix for stat-name matching just like other values.
                    candidate = re.sub(r"\s*2s\s*$", "", candidate, flags=re.I)
                key = key_for(candidate)
                if key in catalog:
                    detected.append(key)
                    index += count
                    break
            else:
                line = lines[index]
                # Ignore a value on its own line, but not unknown alphabetic text.
                if (strict and not re.fullmatch(r"[+-]?\s*\d+(?:[.,]\d+)?\s*%?", line)) or re.search(r"[A-Za-z]", line):
                    unknown.append(line)
                index += 1

        matched = any(key in selected for key in detected)
        # EP39 accepts clear new names, not just names in our catalog.
        # Standard retains its existing catalog-based validation.
        if strict:
            # A catalog stat was read as a complete name. Tesseract can assign
            # low confidence to short game-font words (notably "Amp") even when
            # the recognized phrase is exact, so confidence must not override
            # an unambiguous catalog match.
            catalog_read = bool(detected) and not unknown
            self._last_ocr_valid = catalog_read or self._ep39_text_is_readable(raw, words)
        else:
            self._last_ocr_valid = bool(detected) and (matched or not unknown)
        if not self._last_ocr_valid:
            if strict:
                self._last_ocr_issue = "Unclear OCR text or low word confidence"
            else:
                self._last_ocr_issue = (
                    "Unrecognized text: " + " | ".join(unknown)
                    if unknown else "No recognized pet stat"
                )
        return matched, normalized


    # -------------------------------------------------------------------------
    # 4. รวมระบบตรวจจับและสั่งหยุด (_check_detection_and_stop)
    # -------------------------------------------------------------------------

    def _check_detection_and_stop(self):
        """Confirm a Standard workflow OCR target before stopping."""
        hit, text = self._ocr_match_pet_targets()
        self._last_detection_valid = self._last_ocr_valid
        if hit:
            if not self.safe_sleep_ms(350):
                return True
            hit2, text2 = self._ocr_match_pet_targets()
            if self._last_ocr_valid and hit2 and text == text2:
                self.core.stop("target_found")
                if self.on_target_found:
                    self.on_target_found("ocr", text2)
                return True
            self._last_detection_valid = False
        return False

    def _check_ocr_and_stop(self):
        return self._check_detection_and_stop()
