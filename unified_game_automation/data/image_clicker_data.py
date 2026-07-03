# Image Clicker configuration data and persistence
# Stores image templates, search areas, thresholds, and click settings

import json
import os
import shutil

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

CLICK_TYPES = ["Left Click", "Right Click", "Double Click", "Middle Click"]

SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg")

SUPPORTED_FILETYPES = [("Image files", "*.png *.jpg *.jpeg")]

# Directory to store copied template images (relative to data/)
_TEMPLATES_DIR_NAME = "image_clicker_templates"

# Config file name (lives next to this module)
_CONFIG_FILE_NAME = "image_clicker_config.json"


# --------------------------------------------------------------------------- #
# Default templates
# --------------------------------------------------------------------------- #

def get_default_image_config():
    """Return a fresh default config dict for a single image entry."""
    return {
        "name": "",
        "file_path": "",
        "enabled": True,
        "threshold": 0.85,
        "search_area_name": "Full Screen",
        "click_type": "Left Click",
        "offset_x": 0,
        "offset_y": 0,
        "cooldown_ms": 1000,
    }


def get_default_search_area(name="Full Screen"):
    """Return a fresh default search area dict."""
    return {
        "name": name,
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0,
        "is_full_screen": name == "Full Screen",
    }


def get_default_config():
    """Return the complete default config structure."""
    return {
        "images": [],
        "search_areas": [get_default_search_area("Full Screen")],
    }


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #

def _data_dir():
    """Return the absolute path to the data/ directory."""
    return os.path.dirname(os.path.abspath(__file__))


def get_templates_dir():
    """Return the absolute path to the templates storage directory, creating it if needed."""
    path = os.path.join(_data_dir(), _TEMPLATES_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def get_config_file_path():
    """Return the absolute path to the JSON config file."""
    return os.path.join(_data_dir(), _CONFIG_FILE_NAME)


# --------------------------------------------------------------------------- #
# Image import helper
# --------------------------------------------------------------------------- #

def import_image_file(source_path):
    """
    Copy a template image into the templates directory.

    Returns the destination path, or None on failure.
    """
    if not source_path or not os.path.isfile(source_path):
        return None

    ext = os.path.splitext(source_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None

    templates_dir = get_templates_dir()
    basename = os.path.basename(source_path)

    # Avoid overwriting: append a counter if name exists
    dest_path = os.path.join(templates_dir, basename)
    counter = 1
    name_no_ext, ext_part = os.path.splitext(basename)
    while os.path.exists(dest_path):
        dest_path = os.path.join(templates_dir, f"{name_no_ext}_{counter}{ext_part}")
        counter += 1

    try:
        shutil.copy2(source_path, dest_path)
        return dest_path
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# JSON persistence
# --------------------------------------------------------------------------- #

def save_config(config_dict, path=None):
    """Serialize config to JSON file."""
    path = path or get_config_file_path()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(config_dict, fh, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_config(path=None):
    """
    Deserialize config from JSON file.
    Returns default config if the file is missing or invalid.
    """
    path = path or get_config_file_path()
    if not os.path.isfile(path):
        return get_default_config()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Ensure top-level keys exist
        if "images" not in data:
            data["images"] = []
        if "search_areas" not in data:
            data["search_areas"] = [get_default_search_area("Full Screen")]
        # Ensure "Full Screen" area always exists
        area_names = [a.get("name") for a in data["search_areas"]]
        if "Full Screen" not in area_names:
            data["search_areas"].insert(0, get_default_search_area("Full Screen"))
        return data
    except Exception:
        return get_default_config()
