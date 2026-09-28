"""Small observe/verify/act machine used by stat rerollers."""
from enum import Enum


class Stage(str, Enum):
    OBSERVE = "observe"
    VERIFY = "verify"
    EVALUATE = "evaluate"
    ACT = "act"
    WAIT = "wait"
    REVIEW = "needs_review"


class VerifiedReroll:
    def __init__(self, automation, observe, evaluate, act, on_match, delay_ms=800):
        self.auto = automation
        self.observe = observe
        self.evaluate = evaluate
        self.act = act
        self.on_match = on_match
        self.delay_ms = delay_ms

    def run(self):
        auto = self.auto
        while auto.running and not auto.stop_event.is_set():
            previous = None
            confirmed = None
            for attempt in range(4):
                auto.core.transition(Stage.VERIFY.value if previous else Stage.OBSERVE.value,
                                     f"fresh reading {attempt+1}/4")
                observation = self.observe()
                auto.core.session.observations += 1
                if auto.stop_event.is_set():
                    return
                if observation.valid:
                    signature = tuple((s.name, s.value) for s in observation.stats)
                    if signature == previous:
                        confirmed = observation
                        break
                    previous = signature
                else:
                    previous = None
                    auto.core.session.errors += 1
                    auto.update_status("Unknown reading: " + "; ".join(observation.warnings))
                if not auto.safe_sleep_ms(350):
                    return
            if confirmed is None:
                auto.core.transition(Stage.REVIEW.value, "No stable valid reading; no further clicks")
                auto.core.record_evidence(getattr(auto, "last_image", None))
                auto.core.stop("needs_review")
                return
            auto.core.transition(Stage.EVALUATE.value, confirmed.raw_text)
            decision = self.evaluate(confirmed)
            if decision == "matched":
                auto.core.stop("target_found")
                self.on_match()
                return
            if decision != "absent":
                auto.core.stop("needs_review")
                return
            auto.core.transition(Stage.ACT.value, "Verified target absent")
            if not self.act():
                auto.core.stop("action_failed")
                return
            if auto.core.session.dry_run:
                auto.core.stop("dry_run_complete")
                return
            auto.core.transition(Stage.WAIT.value, "Waiting for game update")
            if not auto.safe_sleep_ms(self.delay_ms):
                return
