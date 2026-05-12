# Pet training system data
# Contains configuration and constants for pet automation

def get_pet_untrain_steps():
    """Return the steps for pet untraining process"""
    return [
        "Pet training",
        "Click on untrain pet icon",
        "Click on wrong slot",
        "Click untrain button",
        "Click yes button"
    ]


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

    return [

        "Normal Attack DMG Up",
        "Critical Rate Up",
        "Ignore Penetration",
        "All Attack UP",
        "Penetration",
        "Critical DMG.",
        "Ignore Accuracy",
        "Defense",
        "Resist Critical Damage",
        "Max Critical Rate",
        "Evasion",
        "Ignore Evasion",
        "Ignore Resist Skill Amp.",
        "Ignore Resist Critical Damage",
        "Aura Mode Duration Increase",
        "Ignore Resist Critical Rate",
        "Resist unable to move",
        "Min Damage"
    ]