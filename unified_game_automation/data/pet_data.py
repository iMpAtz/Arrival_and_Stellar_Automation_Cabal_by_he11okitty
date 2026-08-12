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

        'Accuracy', 
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
        'Resist Skill Amp.', 
        'Resist unable to move',    ]


def get_pet_yolo_class_options():
    """Return the class names for YOLO pet detection.
    Edit this list to match the classes in your trained YOLO26 model.
    These are shown as checkboxes in the UI (same style as OCR targets).
    """
    return [
        'Accuracy',
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
        'Resist Skill Amp.',
        'Resist unable to move',
    ]