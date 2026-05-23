"""
helpers.py - Shared utility functions for Empyrean Bot
All cogs should import from here instead of duplicating code.
"""

import datetime
import random
from utils.constants import RANK_STATS, BREAKTHROUGH_KI, MURIM_EVENTS, FACTIONS, HEARTBEAT_REGEN, BACKGROUNDS

print("[DEBUG] helpers.py: Loading helper functions...")

# ==========================================
# EXISTING FUNCTIONS
# ==========================================

def get_rank_index(rank_name: str) -> int:
    """Convert rank name to index number (0-4)."""
    rank_map = {
        "The Bound (Mortal)": 0,
        "Third-Rate Warrior": 1,
        "Second-Rate Warrior": 2,
        "First-Rate Warrior": 3,
        "Peak Master": 4
    }
    return rank_map.get(rank_name, 0)

def get_rank_from_ki(ki_amount: int) -> str:
    """Determine what rank a user should be based on Ki amount."""
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
    """Get max HP, Vitality, and Ki cap for a rank."""
    stats = RANK_STATS.get(rank_name, RANK_STATS["The Bound (Mortal)"])
    return {
        "max_hp": stats["hp_cap"],
        "max_vit": stats["vit_cap"],
        "ki_cap": stats["ki_cap"]
    }

def get_heartbeat_regen(rank_name: str) -> int:
    """Get heartbeat regeneration amount for a rank."""
    return HEARTBEAT_REGEN.get(rank_name, 25)

def get_breakthrough_ki_required(current_rank: str, background: str = None) -> int:
    """Get Ki required for breakthrough, with Laborer discount."""
    required = BREAKTHROUGH_KI.get(current_rank, 100)

    if background == "Laborer":
        required = int(required * 0.85)

    return required

def get_next_rank(current_rank: str) -> str:
    """Get the next rank name after breakthrough."""
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

def calculate_afk_gains(rank: str, hours_passed: float, profession: str = None, background: str = None) -> dict:
    """Calculate Ki and Mastery gained while offline."""
    from utils.constants import AFK_KI_PER_HOUR, AFK_MASTERY_PER_HOUR

    ki_rate = AFK_KI_PER_HOUR.get(rank, 150)
    ki_gained = int(ki_rate * hours_passed)

    if background == "Hermit":
        ki_gained = int(ki_gained * 1.15)

    mastery_multiplier = 1.15 if profession == "Instructor" else 1.0
    mastery_gained = AFK_MASTERY_PER_HOUR * hours_passed * mastery_multiplier

    return {
        "ki": ki_gained,
        "mastery": mastery_gained
    }

def calculate_stage_from_ki(ki: int, ki_cap: int) -> str:
    """Determine cultivation stage based on current Ki vs cap."""
    from utils.constants import STAGES

    if ki >= ki_cap:
        return "Peak"
    elif ki >= ki_cap * 0.75:
        return "Late"
    elif ki >= ki_cap * 0.50:
        return "Middle"
    else:
        return "Initial"

def has_meridian_damage(meridian_damage_str) -> tuple:
    """Check if user has active meridian damage. Returns (is_damaged, minutes_remaining)."""
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
    """Get starting reputation for a faction."""
    faction_info = FACTIONS.get(faction_name, {})
    return faction_info.get("starting_reputation", 0)

def get_faction_reward(faction_name: str, reputation: int) -> str | None:
    """Get reward string for a faction at given reputation level."""
    faction_info = FACTIONS.get(faction_name, {})
    rewards = faction_info.get("rewards", {})

    achieved_tiers = [tier for tier in rewards.keys() if reputation >= tier]
    if achieved_tiers:
        highest_tier = max(achieved_tiers)
        return rewards.get(highest_tier)
    return None

# ==========================================
# RANDOM EVENT HELPERS
# ==========================================

def roll_random_event():
    """Return a random Murim event from constants.MURIM_EVENTS."""
    event = random.choice(MURIM_EVENTS)
    return event[0], event[1]  # description, effects

def apply_event_effects(user_data: dict, effects: dict) -> dict:
    """Apply event effects to user data."""
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
    """Convert a color name to a Discord hex value."""
    from utils.constants import COLOR_MAIN, COLOR_WIN, COLOR_LOSE, COLOR_GOLD, COLOR_TEAL

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
# TIME HELPER
# ==========================================

def get_timezone_aware_now():
    """Get timezone-aware current time."""
    return datetime.datetime.now(datetime.timezone.utc)

def format_time_remaining(seconds: int) -> str:
    """Format seconds into human-readable time remaining string."""
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
    """Check if a rank name is valid."""
    return rank_name in RANK_STATS

def is_valid_background(background_name: str) -> bool:
    """Check if a background name is valid."""
    return background_name in BACKGROUNDS

def clamp(value: int, min_value: int, max_value: int) -> int:
    """Clamp a value between min and max."""
    return max(min_value, min(value, max_value))

print("[DEBUG] helpers.py: Helper functions loaded successfully")