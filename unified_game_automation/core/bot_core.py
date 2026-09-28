"""Run lifecycle, bounded execution and nonblocking cancellation."""
import json
import queue
import threading
import time
from core.session import RunSession
from core.paths import writable_root


class BotCore:
    def __init__(self, status_callback=None):
        self._status_callback = status_callback
        self._lock = threading.RLock()
        self._local = threading.local()
        self._idle_event = threading.Event()
        self._calibration_cancel = threading.Event()
        self.save_evidence = False
        self._active_threads = {}
        self._running_automation = None
        self._running_tool = None
        self._started_at = None
        self.session = None
        self.completed_runs = queue.Queue()
        self._emergency_handlers = {}
        self._watchdog_stop = threading.Event()
        self._watchdog_thread = None
        self.dry_run = False
        self.max_seconds = 1800
        self.max_actions = 10000
        self.report_dir = writable_root() / "summaries"

    @property
    def stop_event(self):
        session = getattr(self._local, "session", None) or self.session
        return session.cancel if session else self._idle_event

    def set_status_callback(self, callback):
        self._status_callback = callback

    def update_status(self, message):
        if self._status_callback:
            self._status_callback(message)
        else:
            print(message)

    def begin_run(self, tool_name, automation=None):
        with self._lock:
            if self._running_tool or any(t.is_alive() for t in self._active_threads.values()):
                self.update_status("Cannot start: previous run or coordinate capture is still active")
                return False
            self.session = RunSession(tool_name, self.dry_run, self.max_seconds, self.max_actions)
            self._running_tool = tool_name
            self._running_automation = automation
            self._started_at = self.session.started_at
        self.update_status(f"Starting {tool_name}" + (" (DRY RUN)" if self.dry_run else ""))
        return True

    def start(self, automation=None):
        if not self.session or self.session.completed:
            if not self.begin_run(getattr(automation, "name", "Automation"), automation):
                return False
        if self.session.cancel.is_set():
            return False
        self._running_automation = automation or self._running_automation
        return True

    def active_tool(self):
        return self._running_tool

    def is_busy(self):
        return self._running_tool is not None

    def end_run(self, tool_name=None):
        if tool_name and tool_name != self._running_tool:
            return
        # The worker owns completion; UI stop must not allow a premature restart.
        if any(t.is_alive() for t in self._active_threads.values()):
            return
        if self.session:
            self._finish(self.session)

    def stop(self, reason="user_stop"):
        if self.session:
            self.session.stop(reason)
        self._idle_event.set()
        if self._running_automation:
            self._running_automation.running = False
        # Never join a worker on the Tk thread.

    def emergency_stop(self):
        self._calibration_cancel.set()
        self.stop("emergency_stop")
        self.update_status("EMERGENCY STOP requested")
        self.end_run()

    def sleep(self, seconds, step=0.05):
        event = self.stop_event
        deadline = time.monotonic() + max(0, float(seconds))
        while not event.is_set():
            self.heartbeat("waiting")
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                return True
            event.wait(min(max(0.001, step), remaining))
        return False

    def wait_for_mouse_click(self, mouse_module, button="left", poll_sec=0.05):
        # Calibration is not a run and uses a fresh independent event.
        event = self.stop_event if self.is_busy() else self._calibration_cancel
        while not event.is_set():
            if mouse_module.is_pressed(button):
                while mouse_module.is_pressed(button) and not event.wait(poll_sec):
                    pass
                return None if event.is_set() else mouse_module.get_position()
            event.wait(poll_sec)
        return None

    def register_thread(self, name, target, daemon=True, args=(), kwargs=None):
        session = self.session if self.is_busy() else None
        def wrapped():
            self._local.session = session
            try:
                target(*args, **(kwargs or {}))
            except Exception as exc:
                if session:
                    session.errors += 1
                    session.stop("worker_error")
                self.update_status(f"Worker failed: {exc}")
            finally:
                with self._lock:
                    self._active_threads.pop(name, None)
                if session:
                    self._finish(session)
        with self._lock:
            if name in self._active_threads and self._active_threads[name].is_alive():
                raise RuntimeError(f"Worker already active: {name}")
            thread = threading.Thread(target=wrapped, name=name, daemon=daemon)
            self._active_threads[name] = thread
            thread.start()
        return thread

    def unregister_thread(self, name):
        with self._lock:
            self._active_threads.pop(name, None)

    def _finish(self, session):
        with self._lock:
            if session.completed:
                return
            session.completed = True
            session.stop(session.stop_reason or "completed")
            automation = self._running_automation if self.session is session else None
            if automation:
                automation.running = False
            report = session.report()
            report["statistics"] = dict(getattr(automation, "stat_counter", {}))
            report["unmapped_ocr"] = dict(getattr(automation, "unmapped_ocr_counter", {}))
            if self.session is session:
                self._running_tool = None
                self._running_automation = None
                self._started_at = None
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            (self.report_dir / f"run_{session.run_id}.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            self.update_status(f"Could not save run report: {exc}")
        self.completed_runs.put(report)
        self.update_status(f"Stopped {session.tool}: {session.stop_reason}")

    def heartbeat(self, loop_name):
        session = getattr(self._local, "session", None) or self.session
        if session and not session.completed:
            session.heartbeat_at = time.monotonic()
            reason = session.limit_reason()
            if reason:
                session.stop(reason)

    def transition(self, stage, detail=""):
        session = getattr(self._local, "session", None) or self.session
        if session:
            session.transition(stage, detail)
            self.update_status(f"[{session.tool}] {stage}: {detail}")

    def authorize_input(self):
        """Called under the connector's input lock for every click path."""
        worker_session = getattr(self._local, "session", None)
        if self.is_busy() and worker_session is not self.session:
            return False, False  # Background image clicks defer during an exclusive run.
        worker_session = worker_session or getattr(self._local, "background_session", None)
        if worker_session:
            reason = worker_session.limit_reason()
            if reason:
                worker_session.stop(reason)
            if worker_session.cancel.is_set() or worker_session.completed:
                return False, False
            worker_session.actions += 1
            return True, worker_session.dry_run
        return True, self.dry_run

    def register_emergency_handler(self, tool_name, handler):
        self._emergency_handlers[tool_name] = handler

    def start_watchdog(self, timeout_sec=8.0, check_interval_sec=1.0):
        session = self.session
        if not session:
            return
        def watch():
            while not session.cancel.wait(check_interval_sec):
                reason = session.limit_reason()
                if time.monotonic()-session.heartbeat_at > timeout_sec:
                    reason = "watchdog_timeout"
                if reason:
                    session.stop(reason)
                    self.update_status(f"Stopping {session.tool}: {reason}")
                    return
        self._watchdog_thread = threading.Thread(target=watch, name="botcore-watchdog", daemon=True)
        self._watchdog_thread.start()

    def stop_watchdog(self):
        if self.session:
            self.session.cancel.set()

    def register_calibration(self, target):
        if self.is_busy() or any(t.is_alive() for t in self._active_threads.values()):
            self.update_status("Stop the active run/capture before calibrating")
            return False
        self._calibration_cancel = threading.Event()
        self.register_thread("calibration-capture", target)
        return True

    def record_evidence(self, image):
        if not self.save_evidence or image is None or not self.session:
            return
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            image.save(self.report_dir / f"review_{self.session.run_id}.png")
        except OSError as exc:
            self.update_status(f"Could not save review screenshot: {exc}")

    def bind_background(self, session):
        self._local.background_session = session
