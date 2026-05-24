"""
backend/helpers.py - Shared utility functions for Empyrean Bot
All commands should import from here instead of duplicating code.

This file contains pure calculation and helper functions – no database calls.
All game data is imported from backend.constants.
"""

import datetime
import random
from backend.constants import (
    RANK_STATS, BREAKTHROUGH_KI, MURIM_EVENTS, FACTIONS,
    HEARTBEAT_REGEN, BACKGROUNDS, STAGES,
    AFK_KI_PER_HOUR, AFK_MASTERY_PER_HOUR,
    COLOR_MAIN, COLOR_WIN, COLOR_LOSE, COLOR_GOLD, COLOR_TEAL
)

print("[DEBUG] helpers.py: Loading helper functions...")


# ==========================================
# RANK & STATS HELPERS
# ==========================================

def get_rank_index(rank_name: str) -> int:
    """
    Convert rank name to index number (0-4).
    
    Args:
        rank_name (str): Name of the rank (e.g., "Third-Rate Warrior")
        
    Returns:
        int: Index of the rank (0 for Mortal, 4 for Peak Master)
        
    Example:
        idx = get_rank_index("Second-Rate Warrior")  # Returns 2
    """
    rank_map = {
        "The Bound (Mortal)": 0,
        "Third-Rate Warrior": 1,
        "Second-Rate Warrior": 2,
        "First-Rate Warrior": 3,
        "Peak Master": 4
    }
    return rank_map.get(rank_name, 0)


def get_rank_from_ki(ki_amount: int) -> str:
    """
    Determine what rank a user should be based on their Ki amount.
    
    Args:
        ki_amount (int): Current Ki value
        
    Returns:
        str: Rank name based on Ki thresholds
        
    Example:
        rank = get_rank_from_ki(5000)  # Returns "Second-Rate Warrior"
    """
    if ki_amount >= 15000:
        return "Peak Master"
    elif ki_amount >= 7500:
        return "First-Rate Warrior"
    elif ki_amount >= 3000:
        return "Second-Rate Warrior"
    elif ki_amount >= 1000:
        return "Third-Rate Warrior"
    else:
        return "The Bound (Mortal)"


def get_max_stats(rank_name: str) -> dict:
    """
    Get max HP, Vitality, and Ki cap for a rank.
    
    Args:
        rank_name (str): Name of the rank
        
    Returns:
        dict: Contains 'max_hp', 'max_vit', 'ki_cap'
        
    Example:
        stats = get_max_stats("Third-Rate Warrior")
        # Returns {"max_hp": 300, "max_vit": 300, "ki_cap": 1000}
    """
    stats = RANK_STATS.get(rank_name, RANK_STATS["The Bound (Mortal)"])
    return {
        "max_hp": stats["hp_cap"],
        "max_vit": stats["vit_cap"],
        "ki_cap": stats["ki_cap"]
    }


def get_heartbeat_regen(rank_name: str) -> int:
    """
    Get the amount of HP and Vitality restored by heartbeat for a rank.
    
    Args:
        rank_name (str): Name of the rank
        
    Returns:
        int: Regeneration amount (25-250 depending on rank)
    """
    return HEARTBEAT_REGEN.get(rank_name, 25)


# ==========================================
# BREAKTHROUGH HELPERS
# ==========================================

def get_breakthrough_ki_required(current_rank: str, background: str = None) -> int:
    """
    Get the Ki required to attempt a breakthrough to the next rank.
    Laborer background gets a 15% discount.
    
    Args:
        current_rank (str): Current rank name
        background (str, optional): Player's background ("Laborer" gets discount)
        
    Returns:
        int: Ki required for breakthrough
        
    Example:
        required = get_breakthrough_ki_required("The Bound (Mortal)", "Laborer")
        # Returns 85 (instead of 100)
    """
    required = BREAKTHROUGH_KI.get(current_rank, 100)

    if background == "Laborer":
        required = int(required * 0.85)

    return required


def get_next_rank(current_rank: str) -> str:
    """
    Get the next rank name after breakthrough.
    
    Args:
        current_rank (str): Current rank name
        
    Returns:
        str: Next rank name, or the same rank if already at peak
        
    Example:
        next_rank = get_next_rank("Third-Rate Warrior")  # Returns "Second-Rate Warrior"
    """
    rank_order = [
        "The Bound (Mortal)",
        "Third-Rate Warrior",
        "Second-Rate Warrior",
        "First-Rate Warrior",
        "Peak Master"
    ]

    try:
        current_index = rank_order.index(current_rank)
        if current_index < len(rank_order) - 1:
            return rank_order[current_index + 1]
    except ValueError:
        pass

    return current_rank


# ==========================================
# AFK & PROGRESSION HELPERS
# ==========================================

def calculate_afk_gains(rank: str, hours_passed: float, profession: str = None, background: str = None) -> dict:
    """
    Calculate Ki and Mastery gained while offline.
    
    Args:
        rank (str): Current rank name
        hours_passed (float): Number of hours offline
        profession (str, optional): Player's profession (Instructor gets +15% mastery)
        background (str, optional): Player's background (Hermit gets +15% Ki)
        
    Returns:
        dict: Contains 'ki' (int) and 'mastery' (float) gained
        
    Example:
        gains = calculate_afk_gains("Third-Rate Warrior", 2.5, profession="Instructor")
        # Returns {"ki": 750, "mastery": 1.4375}
    """
    ki_rate = AFK_KI_PER_HOUR.get(rank, 150)
    ki_gained = int(ki_rate * hours_passed)

    # Hermit background gives 15% bonus Ki
    if background == "Hermit":
        ki_gained = int(ki_gained * 1.15)

    # Instructor profession gives 15% bonus Mastery
    mastery_multiplier = 1.15 if profession == "Instructor" else 1.0
    mastery_gained = AFK_MASTERY_PER_HOUR * hours_passed * mastery_multiplier

    return {
        "ki": ki_gained,
        "mastery": mastery_gained
    }


def calculate_stage_from_ki(ki: int, ki_cap: int) -> str:
    """
    Determine cultivation stage based on current Ki vs cap.
    
    Stages: Initial (<50%), Middle (50-74%), Late (75-99%), Peak (100%)
    
    Args:
        ki (int): Current Ki amount
        ki_cap (int): Maximum Ki for current rank
        
    Returns:
        str: Stage name ("Initial", "Middle", "Late", or "Peak")
    """
    if ki >= ki_cap:
        return "Peak"
    elif ki >= ki_cap * 0.75:
        return "Late"
    elif ki >= ki_cap * 0.50:
        return "Middle"
    else:
        return "Initial"


# ==========================================
# MERIDIAN DAMAGE HELPERS
# ==========================================

def has_meridian_damage(meridian_damage_str) -> tuple:
    """
    Check if a user has active meridian damage.
    
    Args:
        meridian_damage_str: ISO format timestamp string or None
        
    Returns:
        tuple: (is_damaged (bool), minutes_remaining (int))
        
    Example:
        damaged, minutes = has_meridian_damage(user.get('meridian_damage'))
        if damaged:
            await ctx.send(f"Wait {minutes} minutes.")
    """
    if not meridian_damage_str:
        return (False, 0)

    try:
        exp_time = datetime.datetime.fromisoformat(meridian_damage_str)
        now = datetime.datetime.now()
        if now < exp_time:
            diff = exp_time - now
            minutes = int(diff.total_seconds() // 60)
            return (True, minutes)
    except (ValueError, TypeError):
        pass

    return (False, 0)


# ==========================================
# FACTION HELPERS
# ==========================================

def get_faction_starting_reputation(faction_name: str) -> int:
    """
    Get the starting reputation for a faction.
    
    Args:
        faction_name (str): Name of the faction (Orthodox, Unorthodox, Demonic Cult)
        
    Returns:
        int: Starting reputation (0 for Orthodox/Unorthodox, -50 for Demonic Cult)
    """
    faction_info = FACTIONS.get(faction_name, {})
    return faction_info.get("starting_reputation", 0)


def get_faction_reward(faction_name: str, reputation: int) -> str | None:
    """
    Get the reward string for a faction at a given reputation level.
    
    Args:
        faction_name (str): Name of the faction
        reputation (int): Current reputation value
        
    Returns:
        str or None: Reward description if a threshold is reached, else None
        
    Example:
        reward = get_faction_reward("Orthodox", 75)  # Returns Orthodox amulet reward
    """
    faction_info = FACTIONS.get(faction_name, {})
    rewards = faction_info.get("rewards", {})

    # Find the highest reward tier achieved
    achieved_tiers = [tier for tier in rewards.keys() if reputation >= tier]
    if achieved_tiers:
        highest_tier = max(achieved_tiers)
        return rewards.get(highest_tier)
    return None


# ==========================================
# RANDOM EVENT HELPERS
# ==========================================

def roll_random_event():
    """
    Return a random Murim event from constants.MURIM_EVENTS.
    
    Returns:
        tuple: (description (str), effects (dict))
        
    Example:
        desc, effects = roll_random_event()
        # desc: "🍂 A wandering master shares a breath technique."
        # effects: {"ki": 15}
    """
    event = random.choice(MURIM_EVENTS)
    return event[0], event[1]  # description, effects


def apply_event_effects(user_data: dict, effects: dict) -> dict:
    """
    Apply event effects to user data (Ki, HP, Vitality, Taels, Mastery, Combat Mastery).
    
    Args:
        user_data (dict): Current user data dictionary
        effects (dict): Effects to apply (e.g., {"ki": 15, "hp": -5})
        
    Returns:
        dict: Updated user data with effects applied (values clamped at 0)
        
    Example:
        user = {"ki": 100, "hp": 50}
        user = apply_event_effects(user, {"ki": 20, "hp": -10})
        # user becomes {"ki": 120, "hp": 40}
    """
    result = user_data.copy()

    for key, value in effects.items():
        if key == "ki":
            result["ki"] = max(0, result.get("ki", 0) + value)
        elif key == "hp":
            result["hp"] = max(0, result.get("hp", 0) + value)
        elif key == "vit":
            result["vitality"] = max(0, result.get("vitality", 0) + value)
        elif key == "taels":
            result["taels"] = max(0, result.get("taels", 0) + value)
        elif key == "mastery":
            result["mastery"] = max(0, result.get("mastery", 0) + value)
        elif key == "combat_mastery":
            result["combat_mastery"] = max(0, result.get("combat_mastery", 0) + value)

    return result


# ==========================================
# EMBED COLOR HELPER
# ==========================================

def format_embed_color(color_name: str) -> int:
    """
    Convert a color name to a Discord hex value.
    
    Valid color names:
        "main", "win", "lose", "gold", "teal", "success", "error"
    
    Args:
        color_name (str): Name of the color to use
        
    Returns:
        int: Discord color hex value (e.g., 0x700000 for "main")
        
    Example:
        color = format_embed_color("win")  # Returns 0x00FF00
    """
    colors = {
        "main": COLOR_MAIN,
        "win": COLOR_WIN,
        "lose": COLOR_LOSE,
        "gold": COLOR_GOLD,
        "teal": COLOR_TEAL,
        "success": COLOR_WIN,
        "error": COLOR_LOSE,
    }
    return colors.get(color_name.lower(), COLOR_MAIN)


# ==========================================
# TIME HELPERS
# ==========================================

def get_timezone_aware_now():
    """
    Get timezone-aware current time (UTC).
    
    Returns:
        datetime: Current time with UTC timezone
    """
    return datetime.datetime.now(datetime.timezone.utc)


def format_time_remaining(seconds: int) -> str:
    """
    Format seconds into a human-readable time remaining string.
    
    Args:
        seconds (int): Number of seconds
        
    Returns:
        str: Formatted string (e.g., "1h 30m", "45s", "now")
        
    Example:
        text = format_time_remaining(5430)  # Returns "1h 30m"
    """
    if seconds <= 0:
        return "now"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


# ==========================================
# VALIDATION HELPERS
# ==========================================

def is_valid_rank(rank_name: str) -> bool:
    """
    Check if a rank name is valid (exists in RANK_STATS).
    
    Args:
        rank_name (str): Rank name to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return rank_name in RANK_STATS


def is_valid_background(background_name: str) -> bool:
    """
    Check if a background name is valid (exists in BACKGROUNDS).
    
    Args:
        background_name (str): Background name to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return background_name in BACKGROUNDS


def clamp(value: int, min_value: int, max_value: int) -> int:
    """
    Clamp a value between a minimum and maximum.
    
    Args:
        value (int): Value to clamp
        min_value (int): Minimum allowed value
        max_value (int): Maximum allowed value
        
    Returns:
        int: Clamped value within [min_value, max_value]
        
    Example:
        clamped = clamp(150, 0, 100)  # Returns 100
    """
    return max(min_value, min(value, max_value))


print("[DEBUG] helpers.py: Helper functions loaded successfully")