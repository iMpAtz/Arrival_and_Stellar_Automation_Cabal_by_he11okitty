import threading
import time
from datetime import datetime


class BotCore:
    """Centralized runtime controller for all automation workers."""

    def __init__(self, status_callback=None):
        self.stop_event = threading.Event()
        self._status_callback = status_callback

        self._lock = threading.RLock()
        self._active_threads = {}
        self._running_automation = None
        self._running_tool = None
        self._started_at = None
        self._iteration_count = 0
        self._emergency_handlers = {}
        self._loop_heartbeats = {}

        self._watchdog_stop = threading.Event()
        self._watchdog_thread = None
        self._watchdog_timeout_sec = 8.0
        self._watchdog_check_interval_sec = 1.0

    def set_status_callback(self, callback):
        self._status_callback = callback

    def update_status(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        if self._status_callback:
            self._status_callback(line)
        else:
            print(line)

    def begin_run(self, tool_name, automation=None):
        with self._lock:
            if self._running_tool and self._running_tool != tool_name:
                self.update_status(
                    f"Cannot start {tool_name}: {self._running_tool} is already running"
                )
                return False
            self._running_tool = tool_name
            self._running_automation = automation
            self._started_at = time.time()
            self._iteration_count = 0
            self.stop_event.clear()
        self.update_status(f"Starting {tool_name}")
        return True

    def end_run(self, tool_name=None):
        with self._lock:
            if tool_name and self._running_tool != tool_name:
                return
            finished_tool = self._running_tool
            self._running_tool = None
            self._running_automation = None
            self._started_at = None
            self._loop_heartbeats.clear()
        if finished_tool:
            self.update_status(f"Stopped {finished_tool}")

    def is_busy(self):
        with self._lock:
            return self._running_tool is not None

    def active_tool(self):
        with self._lock:
            return self._running_tool

    def start(self):
        self.stop_event.clear()

    def stop(self):
        self.stop_event.set()
        self._stop_all_registered_threads()
        self.stop_watchdog()

    def emergency_stop(self):
        self.update_status("EMERGENCY STOP requested")
        self.stop_event.set()
        self._call_emergency_handler()
        self._stop_all_registered_threads()
        self.stop_watchdog()
        self.end_run()

    def sleep(self, seconds, step=0.05):
        remaining = max(0.0, float(seconds))
        while remaining > 0:
            if self.stop_event.is_set():
                return False
            wait_time = min(step, remaining)
            self.stop_event.wait(wait_time)
            remaining -= wait_time
        return not self.stop_event.is_set()

    def wait_for_mouse_click(self, mouse_module, button="left", poll_sec=0.05):
        while not self.stop_event.is_set():
            if mouse_module.is_pressed(button):
                while mouse_module.is_pressed(button) and not self.stop_event.is_set():
                    if not self.sleep(poll_sec):
                        return None
                return mouse_module.get_position()
            if not self.sleep(poll_sec):
                return None
        return None

    def register_thread(self, name, target, daemon=True, args=(), kwargs=None):
        kwargs = kwargs or {}

        def wrapped_target():
            try:
                target(*args, **kwargs)
            finally:
                self.unregister_thread(name)

        thread = threading.Thread(target=wrapped_target, name=name, daemon=daemon)
        with self._lock:
            self._active_threads[name] = thread
        thread.start()
        return thread

    def unregister_thread(self, name):
        with self._lock:
            self._active_threads.pop(name, None)

    def _stop_all_registered_threads(self, join_timeout=2.0):
        with self._lock:
            threads = list(self._active_threads.items())
        current_thread = threading.current_thread()
        for _, thread in threads:
            # Never join the thread that is currently executing stop().
            if thread is current_thread:
                continue
            if thread.is_alive():
                thread.join(timeout=join_timeout)
        with self._lock:
            self._active_threads = {
                name: thread for name, thread in self._active_threads.items() if thread.is_alive()
            }

    def register_emergency_handler(self, tool_name, handler):
        with self._lock:
            self._emergency_handlers[tool_name] = handler

    def _call_emergency_handler(self):
        handler = None
        with self._lock:
            if self._running_tool:
                handler = self._emergency_handlers.get(self._running_tool)
        if handler:
            try:
                handler()
            except Exception as exc:
                self.update_status(f"Emergency handler failed: {exc}")

    def heartbeat(self, loop_name):
        with self._lock:
            self._loop_heartbeats[loop_name] = time.time()

    def start_watchdog(self, timeout_sec=8.0, check_interval_sec=1.0):
        with self._lock:
            self._watchdog_timeout_sec = float(timeout_sec)
            self._watchdog_check_interval_sec = float(check_interval_sec)
            if self._watchdog_thread and self._watchdog_thread.is_alive():
                return
            self._watchdog_stop.clear()
            self._watchdog_thread = threading.Thread(
                target=self._watchdog_loop,
                name="botcore-watchdog",
                daemon=True,
            )
            self._watchdog_thread.start()

    def stop_watchdog(self):
        self._watchdog_stop.set()
        with self._lock:
            thread = self._watchdog_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)

    def _watchdog_loop(self):
        while not self._watchdog_stop.is_set():
            with self._lock:
                heartbeats = dict(self._loop_heartbeats)
                running_tool = self._running_tool
                timeout_sec = self._watchdog_timeout_sec

            if running_tool and heartbeats:
                now = time.time()
                for loop_name, last_tick in heartbeats.items():
                    if now - last_tick > timeout_sec:
                        self.update_status(
                            f"Watchdog detected stalled loop '{loop_name}' for {running_tool}"
                        )
                        self.stop_event.set()
                        return

            self._watchdog_stop.wait(self._watchdog_check_interval_sec)
