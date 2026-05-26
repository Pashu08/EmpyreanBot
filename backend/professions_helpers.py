"""
backend/professions_helpers.py - Helper functions for Professions cog

This module handles:
- Progress bar generation
- Profession list and validation
- Profession data management (for future expansion)

All functions are simple and stateless - no complex logic needed yet.
"""

import discord
from typing import List, Tuple, Optional

print("[DEBUG] professions_helpers.py: Loading professions helpers...")


# ==========================================
# CONSTANTS
# ==========================================

# List of all available professions
PROFESSIONS_LIST = [
    "Alchemist",
    "Blacksmith",
    "Herb Gatherer",
    "Formation Master",
    "Instructor"
]

# Rank progression (for future expansion)
# Currently only Apprentice is used, but structure is ready for later
PROFESSION_RANKS = {
    "Apprentice": {"xp_needed": 0, "multiplier": 1.0},
    "Journeyman": {"xp_needed": 1000, "multiplier": 1.2},
    "Adept": {"xp_needed": 3000, "multiplier": 1.5},
    "Expert": {"xp_needed": 6000, "multiplier": 2.0},
    "Master": {"xp_needed": 10000, "multiplier": 3.0},
}

# Placeholder benefits per profession (for future expansion)
# These are just placeholders - actual benefits will be added later
PROFESSION_BENEFITS = {
    "Alchemist": {
        "description": "Expert in pill refining and potion crafting.",
        "placeholder_benefits": ["+20% Ki from pills", "Chance to craft extra potion"]
    },
    "Blacksmith": {
        "description": "Master of weapon forging and armor crafting.",
        "placeholder_benefits": ["+10% damage with weapons", "Can repair gear"]
    },
    "Herb Gatherer": {
        "description": "Skilled at finding medicinal herbs in the wild.",
        "placeholder_benefits": ["+50% herbs from gathering", "Chance to find rare herbs"]
    },
    "Formation Master": {
        "description": "Expert in mystical arrays and combat formations.",
        "placeholder_benefits": ["+10% dodge in combat", "Can set formations"]
    },
    "Instructor": {
        "description": "Wise teacher who guides others on the martial path.",
        "placeholder_benefits": ["+15% Mastery gain", "Can teach techniques"]
    },
}


# ==========================================
# PROFESSION HELPERS
# ==========================================

def get_professions_list() -> List[str]:
    """
    Get the list of all available professions.
    
    Returns:
        List[str]: List of profession names
    """
    return PROFESSIONS_LIST.copy()


def is_valid_profession(profession_name: str) -> bool:
    """
    Check if a profession name is valid.
    
    Args:
        profession_name: Name of the profession to check
        
    Returns:
        bool: True if valid, False otherwise
    """
    return profession_name.title() in PROFESSIONS_LIST


def get_profession_benefits(profession_name: str) -> dict:
    """
    Get the benefits/description for a profession.
    
    Args:
        profession_name: Name of the profession
        
    Returns:
        dict: Benefits data for the profession
    """
    return PROFESSION_BENEFITS.get(profession_name, {})


# ==========================================
# RANK HELPERS (for future expansion)
# ==========================================

def get_rank_from_xp(xp: int) -> str:
    """
    Determine rank based on XP.
    
    Currently returns "Apprentice" for all XP values since
    rank progression is not yet implemented.
    
    Args:
        xp: Current experience points
        
    Returns:
        str: Rank name (always "Apprentice" for now)
    """
    # For future expansion when rank progression is added:
    # ranks = ["Apprentice", "Journeyman", "Adept", "Expert", "Master"]
    # thresholds = [0, 1000, 3000, 6000, 10000]
    # for i, threshold in enumerate(thresholds):
    #     if xp < thresholds[i + 1] if i + 1 < len(thresholds) else True:
    #         return ranks[i]
    # return "Master"
    
    # Currently just return Apprentice
    return "Apprentice"


def get_next_rank_xp(current_rank: str) -> int:
    """
    Get XP needed for the next rank.
    
    Args:
        current_rank: Current rank name
        
    Returns:
        int: XP needed for next rank, or 0 if at max rank
    """
    # For future expansion
    rank_order = ["Apprentice", "Journeyman", "Adept", "Expert", "Master"]
    
    if current_rank not in rank_order:
        return 1000
    
    current_index = rank_order.index(current_rank)
    if current_index >= len(rank_order) - 1:
        return 0  # Already at max rank
    
    next_rank = rank_order[current_index + 1]
    return PROFESSION_RANKS.get(next_rank, {}).get("xp_needed", 1000)


def get_rank_multiplier(rank: str) -> float:
    """
    Get the XP multiplier for a given rank.
    
    Args:
        rank: Rank name
        
    Returns:
        float: XP multiplier (default 1.0)
    """
    return PROFESSION_RANKS.get(rank, {}).get("multiplier", 1.0)


# ==========================================
# PROGRESS BAR HELPER
# ==========================================

def progress_bar(current: int, required: int) -> Tuple[str, int]:
    """
    Generate a visual progress bar and percentage.
    
    Args:
        current: Current XP value
        required: XP required for next rank
        
    Returns:
        Tuple[str, int]: (progress_bar_string, percentage)
        
    Example:
        >>> bar, percent = progress_bar(750, 1000)
        >>> print(bar)
        '🟥🟥🟥🟥🟥🟥🟥⬛⬛⬛'
        >>> print(percent)
        75
    """
    segments = 10
    # Calculate ratio (0.0 to 1.0)
    ratio = max(0.0, min(current / required, 1.0))
    
    # Calculate filled segments
    filled = int(ratio * segments)
    
    # Build the bar
    bar = "🟥" * filled + "⬛" * (segments - filled)
    
    # Calculate percentage
    percent = int(ratio * 100)
    
    return bar, percent


# ==========================================
# VALIDATION HELPERS
# ==========================================

def validate_profession_choice(profession_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a profession choice.
    
    Args:
        profession_name: The profession name to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
        
    Example:
        >>> is_valid, error = validate_profession_choice("Alchemist")
        >>> print(is_valid)
        True
    """
    if not profession_name:
        return False, "No profession specified."
    
    if not is_valid_profession(profession_name):
        valid_list = ", ".join(PROFESSIONS_LIST)
        return False, f"`{profession_name}` is not a valid profession. Valid options: {valid_list}"
    
    return True, None


print("[DEBUG] professions_helpers.py: Professions helpers loaded successfully")