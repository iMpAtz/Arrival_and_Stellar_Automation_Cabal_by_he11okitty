"""Versioned portable bundles of saved tab settings. Never accept arbitrary destinations."""
import copy
import json
from pathlib import Path
import shutil
import uuid
from data.pet_data import normalize_pet_config, PET_CONFIG_VERSION

CONFIGS = ("arrival_config.json", "stellar_config.json", "heil_config.json",
           "mail_config.json", "pet_config.json", "macro_config.json", "image_clicker_config.json")


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _assets(value, transform):
    if isinstance(value, dict):
        return {k: transform(v) if k == "file_path" and v
                else _assets(v, transform) for k, v in value.items()}
    if isinstance(value, list):
        return [_assets(v, transform) for v in value]
    return value


def export_profile(data_dir, destination):
    data_dir, destination = Path(data_dir), Path(destination)
    settings = {name: json.loads((data_dir/name).read_text(encoding="utf-8"))
                for name in CONFIGS if (data_dir/name).is_file()}
    if "pet_config.json" in settings:
        settings["pet_config.json"] = normalize_pet_config(settings["pet_config.json"])
    asset_dir = destination.parent / (destination.stem + "_assets")
    def copy_asset(value):
        source = Path(value)
        if not source.is_absolute():
            source = data_dir/source
        if not source.is_file():
            raise ValueError(f"Missing profile asset: {source}")
        asset_dir.mkdir(parents=True, exist_ok=True)
        target = asset_dir / (uuid.uuid4().hex + source.suffix)
        shutil.copy2(source, target)
        return target.relative_to(destination.parent).as_posix()
    settings = _assets(settings, copy_asset)
    atomic_json(destination, {"schema_version": 1, "settings": settings})


def import_profile(source, data_dir):
    source, data_dir = Path(source).resolve(), Path(data_dir).resolve()
    profile = json.loads(source.read_text(encoding="utf-8"))
    if profile.get("schema_version") != 1 or not isinstance(profile.get("settings"), dict):
        raise ValueError("Unsupported profile schema")
    settings = copy.deepcopy(profile["settings"])
    if any(name not in CONFIGS or not isinstance(value, dict) for name, value in settings.items()):
        raise ValueError("Profile contains unknown or invalid settings")
    for name, value in settings.items():
        versions = range(1, PET_CONFIG_VERSION + 1) if name == "pet_config.json" else (1, 2)
        if value.get("schema_version", 1) not in versions:
            raise ValueError(f"Unsupported tab settings version: {name}")
    if "pet_config.json" in settings:
        settings["pet_config.json"] = normalize_pet_config(settings["pet_config.json"])
    # Reject non-finite numeric values before importing any files.
    json.dumps(settings, allow_nan=False)
    # Validate every asset before writing any tab settings.
    def validate_asset(value):
        path = (source.parent/value).resolve()
        if not path.is_relative_to(source.parent) or not path.is_file():
            raise ValueError("Missing or unsafe profile asset path")
        return str(path)
    settings = _assets(settings, validate_asset)
    def copy_asset(value):
        asset_dir = data_dir / "profile_assets"
        asset_dir.mkdir(parents=True, exist_ok=True)
        target = asset_dir / (uuid.uuid4().hex + Path(value).suffix)
        shutil.copy2(value, target)
        return str(target)
    settings = _assets(settings, copy_asset)
    for name, value in settings.items():
        target = data_dir/name
        if target.exists():
            shutil.copy2(target, target.with_suffix(".json.bak"))
        atomic_json(target, value)
    return list(settings)
