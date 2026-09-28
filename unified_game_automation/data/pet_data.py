# Pet training system data
# Contains configuration and constants for pet automation

PET_CONFIG_VERSION = 4
PET_CONFIG_KEYS = frozenset({
    "schema_version", "workflow_mode", "step_coords", "ocr_area", "delay_ms",
    "selected_ocr_options",
    # Preserve original OCR-only profile fields when importing older settings.
    "pet_training_coords", "untrain_pet_icon_coords", "wrong_slot_coords",
    "untrain_button_coords", "yes_button_coords", "ocr_search_text", "enabled",
})


def normalize_pet_config(config):
    """Keep supported OCR settings and discard obsolete detector settings."""
    result = {key: value for key, value in config.items() if key in PET_CONFIG_KEYS}
    result["schema_version"] = PET_CONFIG_VERSION
    return result

def get_pet_untrain_steps():
    """Return the steps for pet untraining process"""
    return [
        "Pet training",
        "Click on untrain pet icon",
        "Click on wrong slot",
        "Click untrain button",
        "Click yes button"
    ]


def get_pet_ep39_steps():
    """Convert, OK and Cancel positions for the EP39 reroll workflow."""
    return ["EP39 Click 1", "EP39 Click 2", "EP39 Click 3"]


def get_default_pet_delay():
    """Return default delay for pet automation in milliseconds"""
    return 800


def get_pet_config_template():
    """Return a template configuration for pet automation"""
    return {
        "pet_training_coords": None,
        "untrain_pet_icon_coords": None,
        "wrong_slot_coords": None,
        "untrain_button_coords": None,
        "yes_button_coords": None,
        "ocr_search_text": "",
        "delay_ms": 800,
        "enabled": False
    }
def get_pet_ocr_options():

    return ['Accuracy', 
            'All Attack UP', 
            'All Skill Amp. UP', 
            'Alz drop amount', 
            'Aura Mode Duration Increase', 
            'Cancel Ignore Evasion', 
            'Cancel Ignore Penetration', 
            'Critical DMG.', 
            'Critical Rate Up', 
            'Defense', 
            'Drop 2 slot item', 
            'Evasion', 
            'Ignore Accuracy', 
            'Ignore Evasion', 
            'Ignore Penetration', 
            'Ignore Resist Critical Damage', 
            'Ignore Resist Critical Rate', 
            'Ignore Resist Down', 
            'Ignore Resist Knockback', 
            'Ignore Resist Skill Amp.', 
            'Ignore Resist Stun', 
            'Max Critical Rate', 
            'Min Damage', 
            'Normal Attack DMG Up', 
            'Penetration', 
            'Resist Critical Damage', 
            'Resist Critical Rate', 
            'Resist Skill Amp', 
            'Resist unable to move',
            'STR',
            'INT',
            'DEX',
            'Resist Down',
            'Resist Knockback',
            'Resist Stun',
            'HP',
            'Attack Rate',
            'Add. Damage',
            'Defense Rate',
            'Damage Reduction',
            'HP Auto Heal',
            'Ignore Damage Reduction',
            'Cancel Ignore Damage Reduction',
            'MP',
            'MP Auto Heal',
            'Skill EXP',
            'HP Absorb',
            'MP Absorb',
            'Max HP Steal per hit',
            'Max MP Steal per hit',
            'Increase Box Drop Rate', ]
