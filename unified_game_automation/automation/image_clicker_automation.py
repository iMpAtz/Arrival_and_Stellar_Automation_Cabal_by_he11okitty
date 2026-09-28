# Image Clicker automation logic
# Detects template images on screen using OpenCV and performs configurable clicks
#
# DESIGN NOTE: This automation is intentionally self-contained — it uses its
# own threading.Event and manages its own thread instead of piggybacking on
# BotCore's shared stop_event / watchdog / mutual-exclusion.  This means it
# keeps running continuously regardless of what other automations do, and only
# stops when the user explicitly presses Stop or the hotkey.

import time
import os
import threading
import copy

import cv2
import numpy as np
from PIL import Image


class ImageClickerAutomation:
    """Standalone automation that detects template images and clicks on them.

    Unlike other automations that extend BaseAutomation and share BotCore's
    stop_event, this class manages its own lifecycle so it never gets killed
    by the shared stop mechanism.
    """

    def __init__(self, game_connector, status_callback=None, runtime_core=None):
        self.runtime_core = runtime_core
        self.session = None
        self.game_connector = game_connector
        self._status_callback = status_callback

        # Own stop control — independent of BotCore
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

        # Configuration (set from the UI before starting)
        self._image_configs = []   # list[dict]
        self._search_areas = []    # list[dict]

        # Per-image cooldown tracking: file_path → last_click_timestamp
        self._last_clicked_at = {}

        # Cached template images: file_path → numpy array (or None if failed)
        self._template_cache = {}

        # Stats
        self.detection_count = 0
        self.click_count = 0

        from core.template_matcher import TemplateMatcher
        self.matcher = TemplateMatcher()
        self._frame_cache = {}
        self.running = False
        self._scan_interval_ms = 200  # ms between full scan cycles

    # ------------------------------------------------------------------ #
    # Status helper
    # ------------------------------------------------------------------ #

    def update_status(self, message):
        if self._status_callback:
            self._status_callback(f"[ImageClicker] {message}")

    # ------------------------------------------------------------------ #
    # Configuration setters (called from UI)
    # ------------------------------------------------------------------ #

    def set_image_configs(self, configs):
        self._image_configs = copy.deepcopy(configs) if configs else []
        self._template_cache.clear()

    def set_search_areas(self, areas):
        self._search_areas = copy.deepcopy(areas) if areas else []

    def set_scan_interval(self, ms):
        self._scan_interval_ms = max(50, int(ms))

    # ------------------------------------------------------------------ #
    # Template loading
    # ------------------------------------------------------------------ #

    def _load_template(self, file_path):
        if file_path in self._template_cache:
            return self._template_cache[file_path]
        if not file_path or not os.path.isfile(file_path):
            self._template_cache[file_path] = None
            return None
        try:
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                self._template_cache[file_path] = None
                return None
            self._template_cache[file_path] = img
            return img
        except Exception:
            self._template_cache[file_path] = None
            return None

    # ------------------------------------------------------------------ #
    # Search area resolution
    # ------------------------------------------------------------------ #

    def _resolve_search_area(self, area_name):
        """Return (left, top, width, height) in screen coords."""
        area_def = None
        for a in self._search_areas:
            if a.get("name") == area_name:
                area_def = a
                break
        if area_def is None:
            area_def = {"is_full_screen": True}

        if area_def.get("is_full_screen"):
            rect = self.game_connector.get_window_rect()
            if not rect:
                return None
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)

        x = int(area_def.get("x", 0))
        y = int(area_def.get("y", 0))
        w = int(area_def.get("width", 0))
        h = int(area_def.get("height", 0))
        if w <= 0 or h <= 0:
            return None
        return (x, y, w, h)

    # ------------------------------------------------------------------ #
    # Click execution
    # ------------------------------------------------------------------ #

    def _perform_click(self, click_type, screen_x, screen_y):
        """Execute a click at screen coordinates with client-area adjustment."""
        if not self.game_connector.is_connected():
            if not self.game_connector.connect_to_game():
                return False

        rel_x, rel_y, ok = self.game_connector.convert_to_window_coords(
            screen_x, screen_y
        )
        if not ok:
            return False

        if click_type == "Right Click":
            return self.game_connector.right_click_at_position((rel_x, rel_y))
        elif click_type == "Middle Click":
            return self.game_connector.middle_click_at_position((rel_x, rel_y))
        elif click_type == "Double Click":
            return self.game_connector.double_click_at_position((rel_x, rel_y))
        else:
            return self.game_connector.click_at_position((rel_x, rel_y))

    # ------------------------------------------------------------------ #
    # Own sleep — independent of BotCore
    # ------------------------------------------------------------------ #

    def _sleep_ms(self, ms):
        """Sleep for *ms* milliseconds, returning False if stop was requested."""
        seconds = max(0.0, ms / 1000.0)
        step = 0.05
        while seconds > 0:
            if self._stop_event.is_set():
                return False
            wait = min(step, seconds)
            self._stop_event.wait(wait)
            seconds -= wait
        return not self._stop_event.is_set()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def _validate_config(self):
        enabled = [c for c in self._image_configs if c.get("enabled")]
        if not enabled:
            return False, "No enabled images configured"
        for cfg in enabled:
            try:
                if not 0 <= float(cfg.get("threshold", 0.85)) <= 1:
                    raise ValueError
                if not 0.5 <= float(cfg.get("scale_min", 1)) <= float(cfg.get("scale_max", 1)) <= 2:
                    raise ValueError
                if int(cfg.get("cooldown_ms", 1000)) < 0:
                    raise ValueError
            except (ValueError, TypeError):
                return False, "Invalid threshold, scale range, or cooldown"
            fp = cfg.get("file_path", "")
            if not fp or not os.path.isfile(fp):
                return False, f"Image file not found: {fp}"
        return True, ""

    def start(self):
        is_ok, msg = self._validate_config()
        if not is_ok:
            self.update_status(msg)
            return False

        if not self.game_connector.is_connected():
            if not self.game_connector.connect_to_game():
                self.update_status("Game is not connected")
                return False

        with self._lock:
            if self.running or (self._thread and self._thread.is_alive()):
                self.update_status("Already running")
                return False

            # Reset
            self.detection_count = 0
            self.click_count = 0
            self._last_clicked_at.clear()
            self._template_cache.clear()
            from core.session import RunSession
            core = self.runtime_core
            self.session = RunSession("Image Clicker", bool(core and core.dry_run),
                                      core.max_seconds if core else 1800,
                                      core.max_actions if core else 10000)
            self._stop_event = self.session.cancel
            self.running = True

            self._thread = threading.Thread(
                target=self._run_session_loop,
                name="image-clicker-loop",
                daemon=True,
            )
            self._thread.start()

        self.update_status("Image Clicker started")
        return True

    def stop(self):
        with self._lock:
            was_running = self.running
            self.running = False
            self._stop_event.set()
            if self.session:
                self.session.stop("user_stop")

        if was_running:
            self.update_status(
                f"Image Clicker stopped — Detections: {self.detection_count}, Clicks: {self.click_count}"
            )

    def emergency_stop(self):
        if self.session:
            self.session.stop("emergency_stop")
        self.running = False
        self._stop_event.set()
        self.update_status("🚨 EMERGENCY STOP — Image Clicker stopped!")

    # ------------------------------------------------------------------ #
    # Main worker loop
    # ------------------------------------------------------------------ #

    def _automation_loop(self):
        self.update_status("🖱️ Image Clicker scanning started")

        while self.running and not self._stop_event.is_set():
            reason = self.session.limit_reason() if self.session else ""
            if reason:
                self.session.stop(reason)
                break
            self._frame_cache.clear()
            enabled_configs = [c for c in self._image_configs if c.get("enabled")]

            for cfg in enabled_configs:
                if not self.running or self._stop_event.is_set():
                    break
                try:
                    self._process_single_image(cfg)
                except Exception as e:
                    self.update_status(f"⚠️ Error processing image: {e}")

            # Sleep between full scan cycles
            if not self._sleep_ms(self._scan_interval_ms):
                break

        self.running = False
        self.update_status(
            f"Image Clicker finished — Detections: {self.detection_count}, Clicks: {self.click_count}"
        )

    def _process_single_image(self, cfg):
        file_path = cfg.get("file_path", "")
        threshold = float(cfg.get("threshold", 0.85))
        area_name = cfg.get("search_area_name", "Full Screen")
        click_type = cfg.get("click_type", "Left Click")
        offset_x = int(cfg.get("offset_x", 0))
        offset_y = int(cfg.get("offset_y", 0))
        cooldown_ms = int(cfg.get("cooldown_ms", 1000))
        img_name = cfg.get("name", os.path.basename(file_path))

        # Cooldown check
        now = time.time()
        last = self._last_clicked_at.get(file_path, 0)
        if (now - last) * 1000 < cooldown_ms:
            return

        # Load template
        template = self._load_template(file_path)
        if template is None:
            return

        # Capture search area
        area_rect = self._resolve_search_area(area_name)
        if area_rect is None:
            return

        if area_rect not in self._frame_cache:
            self._frame_cache[area_rect] = self.game_connector.take_screenshot(area_rect)
        screenshot = self._frame_cache[area_rect]
        if screenshot is None:
            return

        # Convert PIL → numpy grayscale
        try:
            if isinstance(screenshot, Image.Image):
                screen_np = np.array(screenshot.convert("L"))
            else:
                screen_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGR2GRAY)
        except Exception:
            return

        # Ensure template fits inside screenshot
        if (template.shape[0] > screen_np.shape[0] or
                template.shape[1] > screen_np.shape[1]):
            return

        found = self.matcher.match(screen_np, template, float(cfg.get("scale_min", 1.0)),
                                   float(cfg.get("scale_max", 1.0)))
        if found is None:
            return
        max_val, max_loc, (templ_w, templ_h) = found

        if max_val < threshold:
            return

        # Detection!
        self.detection_count += 1

        center_x = area_rect[0] + max_loc[0] + templ_w // 2 + offset_x
        center_y = area_rect[1] + max_loc[1] + templ_h // 2 + offset_y

        self.update_status(
            f"🎯 Detected '{img_name}' (confidence {max_val:.3f}) → {click_type}"
        )

        if self._stop_event.is_set():
            return
        if self._perform_click(click_type, center_x, center_y):
            self._frame_cache.clear()  # Any action invalidates previously captured pixels.
            self.click_count += 1
            self._last_clicked_at[file_path] = time.time()
            self.update_status(
                f"✅ Clicked '{img_name}' at ({center_x}, {center_y})"
            )
        else:
            self.update_status(f"⚠️ Click failed for '{img_name}'")

    def _run_session_loop(self):
        from core.profiles import atomic_json
        from core.paths import writable_root
        if self.runtime_core:
            self.runtime_core.bind_background(self.session)
        try:
            self._automation_loop()
        except Exception as exc:
            self.session.errors += 1
            self.session.stop("worker_error")
            self.update_status(str(exc))
        finally:
            self.running = False
            self.session.stop(self.session.stop_reason or "completed")
            self.session.completed = True
            report = self.session.report()
            report.update({"detections": self.detection_count, "clicks": self.click_count})
            directory = self.runtime_core.report_dir if self.runtime_core else writable_root()/"summaries"
            try:
                atomic_json(directory/f"run_{self.session.run_id}.json", report)
            except OSError as exc:
                self.update_status(f"Could not save report: {exc}")
            self.update_status(f"Stopped: {self.session.stop_reason}")
