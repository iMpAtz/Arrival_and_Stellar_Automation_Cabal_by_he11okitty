import re
import time


class BaseAutomation:
    """Thread-safe base class for all automations."""

    def __init__(self, game_connector, ocr_engine=None, bot_core=None, name="Automation"):
        self.game_connector = game_connector
        self.ocr_engine = ocr_engine
        self.core = bot_core
        self.name = name
        self.delay_ms = 800
        self.running = False
        self._last_ocr_hit_at = 0.0
        self._ocr_debounce_sec = 0.4

    @property
    def stop_event(self):
        if self.core:
            return self.core.stop_event
        raise RuntimeError("BotCore is required for BaseAutomation")

    def update_status(self, message):
        if self.core:
            self.core.update_status(f"[{self.name}] {message}")

    def set_delay(self, delay_ms):
        self.delay_ms = max(0, int(delay_ms))

    def start(self):
        if not self.core:
            return False
        self.running = True
        self.core.start()
        return True

    def stop(self):
        self.running = False
        if self.core:
            self.core.stop()

    def emergency_stop(self):
        self.running = False
        if self.core:
            self.core.emergency_stop()

    def safe_sleep_ms(self, delay_ms=None):
        if not self.core:
            return False
        wait_ms = self.delay_ms if delay_ms is None else delay_ms
        return self.core.sleep(float(wait_ms) / 1000.0)

    def safe_loop(self, loop_name, callback):
        if not self.core:
            return
        while self.running and not self.core.stop_event.is_set():
            self.core.heartbeat(loop_name)
            keep_running = callback()
            if not keep_running:
                break

    def protected_click(self, coords, label="", post_delay_ms=None):
        if not self.running or self.stop_event.is_set() or not coords:
            return False
        if not self.game_connector.is_connected() and not self.game_connector.connect_to_game():
            self.update_status("Game is not connected")
            return False
        ok = self.game_connector.click_at_position(coords)
        if ok and label:
            self.update_status(f"Click {label}")
        if ok and post_delay_ms is not None:
            return self.safe_sleep_ms(post_delay_ms)
        return ok

    @staticmethod
    def normalize_text(raw_text):
        text = re.sub(r"[^A-Za-z0-9\s]", " ", raw_text or "")
        text = re.sub(r"\s+", " ", text).strip().lower()
        return text

    def ocr_match_any(self, area, targets):
        if not self.ocr_engine or not area or not targets:
            return False, ""
        screenshot = self.game_connector.take_screenshot(area)
        if screenshot is None:
            return False, ""
        raw = self.ocr_engine.extract_text(screenshot)
        normalized = self.normalize_text(raw)
        now = time.time()
        for target in targets:
            if self.normalize_text(target) in normalized:
                if now - self._last_ocr_hit_at < self._ocr_debounce_sec:
                    return False, normalized
                self._last_ocr_hit_at = now
                return True, normalized
        return False, normalized
