"""Offline observations use the same parser/evaluator as live workers."""
from core.observations import parse_stats, evaluate
from data.arrival_data import get_all_base_stat_names
from data.stellar_data import get_stellar_options


def analyze_image(image, tool, engine, constraints=()):
    raw = engine.extract_text(image, fresh=True)
    catalog = get_stellar_options() if tool == "Stellar" else get_all_base_stat_names()
    observation = parse_stats(raw, catalog, stellar=tool == "Stellar")
    result = observation.to_dict()
    result["decision"] = evaluate(observation, constraints) if constraints else "no_targets"
    result["ocr_error"] = engine.last_error
    return result
