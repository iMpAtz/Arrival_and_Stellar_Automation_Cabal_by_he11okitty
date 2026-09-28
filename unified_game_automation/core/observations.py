"""Conservative stat parsing shared by live automation and offline replay."""
from dataclasses import dataclass, asdict
import re


def normalize_name(text):
    return re.sub(r"[^a-z]", "", text.lower()).replace("critical", "crit").replace("damage", "dmg")


def normalize_numbers(text):
    # Remove only correctly grouped thousands separators, never decimal punctuation.
    return re.sub(r"\b\d{1,3}(?:[,\u2009 ]\d{3})+\b",
                  lambda m: re.sub(r"\D", "", m[0]), text)


@dataclass(frozen=True)
class StatReading:
    name: str
    value: int | None
    raw: str


@dataclass(frozen=True)
class Observation:
    raw_text: str
    stats: tuple = ()
    warnings: tuple = ()

    @property
    def valid(self):
        return bool(self.stats) and not self.warnings and all(s.value is not None for s in self.stats)

    def to_dict(self):
        return asdict(self)


def parse_stats(raw, catalog, stellar=False):
    aliases = {normalize_name(name): name for name in catalog}
    aliases.update({"skillcooltimedecreased": "Skill Cool Time decreased.",
                    "arrivalskillcooltimedecreased": "Skill Cool Time decreased.",
                    "arrivalskillbufftimeup": "Arrival Skill Buff Time UP",
                    "arrivalskilldurationincrease": "Arrival Skill Buff Time UP"} if not stellar else {})
    stats, warnings = [], []
    lines = [line.strip() for line in normalize_numbers(raw or "").splitlines() if line.strip()]
    # Stellar has a separate force line; associate it only with exactly one stat.
    force = None
    if stellar:
        force_lines = [line for line in lines if "stellarforce" in normalize_name(line)]
        if len(force_lines) == 1:
            match = re.search(r"(?:\+|\b4\s+)\s*(\d+)\s*[.]*$", force_lines[0])
            if match:
                force = int(match[1])
    for line in lines:
        key = normalize_name(line)
        if stellar and (key == "stellar" or "stellarforce" in key):
            continue
        # Numeric suffix must be complete: 1.5 and 1,20 are ambiguous, not 1.
        match = re.search(r"(?:\+|-)\s*(\d+)\s*(?:%|s)?\s*[.]*$", line)
        if not match:
            match = re.search(r"\s(\d+)\s*(?:%|s)?\s*[.]*$", line)
        name_text = line[:match.start()].strip() if match else line
        name_text = re.sub(r"\s+4$", "", name_text)
        name_key = normalize_name(name_text)
        if name_key.startswith("stellar"):
            name_key = name_key[len("stellar"):]
        name = aliases.get(name_key)
        if not name and not stellar:
            if name_key.startswith("arrivalskillcooltimedecreas"):
                name = "Skill Cool Time decreased."
            elif name_key.startswith("arrivalskillduration"):
                name = "Arrival Skill Buff Time UP"
        if name:
            value = int(match[1]) if match else force
            stats.append(StatReading(name, value, line))
        else:
            warnings.append(f"Unrecognized line: {line}")
    if stellar and len(stats) != 1:
        warnings.append("Expected exactly one Stellar option")
    if not stats:
        warnings.append("No recognized stats")
    return Observation(raw or "", tuple(stats), tuple(warnings))


def evaluate(observation, constraints):
    if not observation.valid:
        return "unknown"
    for reading in observation.stats:
        for name, minimum in constraints:
            if normalize_name(reading.name) == normalize_name(name) and reading.value >= minimum:
                return "matched"
    return "absent"
