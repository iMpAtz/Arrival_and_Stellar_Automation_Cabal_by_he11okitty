"""Per-run state. Cancellation events are never cleared or reused."""
from dataclasses import dataclass, field
from collections import deque
import threading
import time
import uuid


@dataclass
class RunSession:
    tool: str
    dry_run: bool = False
    max_seconds: float = 1800
    max_actions: int = 10000
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cancel: threading.Event = field(default_factory=threading.Event)
    started_at: float = field(default_factory=time.time)
    started_monotonic: float = field(default_factory=time.monotonic)
    heartbeat_at: float = field(default_factory=time.monotonic)
    stage: str = "validate"
    stop_reason: str = ""
    actions: int = 0
    errors: int = 0
    observations: int = 0
    completed: bool = False
    events: deque = field(default_factory=lambda: deque(maxlen=200))

    def transition(self, stage, detail=""):
        self.stage = stage
        self.heartbeat_at = time.monotonic()
        self.events.append({"elapsed": round(self.heartbeat_at-self.started_monotonic, 3),
                            "stage": stage, "detail": str(detail)[:500]})

    def stop(self, reason):
        if not self.stop_reason:
            self.stop_reason = reason
        self.cancel.set()

    def limit_reason(self):
        if self.max_seconds and time.monotonic()-self.started_monotonic >= self.max_seconds:
            return "time_limit"
        if self.max_actions and self.actions >= self.max_actions:
            return "action_limit"
        return ""

    def report(self):
        return {"schema_version": 1, "run_id": self.run_id, "tool": self.tool,
                "dry_run": self.dry_run, "started_at": self.started_at,
                "elapsed_seconds": round(time.monotonic()-self.started_monotonic, 3),
                "stop_reason": self.stop_reason, "stage": self.stage,
                "actions": self.actions, "errors": self.errors,
                "observations": self.observations, "events": list(self.events)}
