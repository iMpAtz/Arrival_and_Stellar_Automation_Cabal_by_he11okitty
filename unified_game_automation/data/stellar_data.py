# Stellar system options and data
# Extracted from main.py

# Stellar system options
STELLAR_OPTIONS = [
    "PVE Penetration",
    "PVE Critical DMG",
    "All Attack UP",
    "Penetration",
    "Critical DMG.",
    "Ignore Accuracy",
    "Defense",
    "Resist Critical Damage",
    "PVP Resist All Skill Amp. UP",
    "Normal Attack DMG Up",
    "Cancel Ignore Penetration",
    "Final Damage increased",
    "Final Damage decreased",
    "Max Critical Rate",
    "Ignore Resist Skill Amp",
    "Ignore Resist Critical Rate",
    "Ignore Penetration",
    "Ignore Resist Critical Damage",
    "Resist Skill Amp",
    
]

# Exceptions for penetration option (from main.py)
PENETRATION_EXCEPTIONS = [
    "ignore",
]

def get_stellar_options():
    """Get all available stellar options"""
    return STELLAR_OPTIONS

def get_penetration_exceptions():
    """Get penetration exceptions"""
    return PENETRATION_EXCEPTIONS
