"""
helpers.py - Shared utility functions for Empyrean Bot
All cogs should import from here instead of duplicating code.
"""

import datetime
from utils.constants import RANK_STATS, BREAKTHROUGH_KI

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

def get_breakthrough_ki_required(current_rank: str, background: str = None) -> int:
    """Get Ki required for breakthrough, with Laborer discount."""
    from utils.constants import BREAKTHROUGH_KI
    
    required = BREAKTHROUGH_KI.get(current_rank, 100)
    
    # Laborer gets 15% discount
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
    
    mastery_multiplier = 1.15 if profession == "Instructor" else 1.0
    mastery_gained = AFK_MASTERY_PER_HOUR * hours_passed * mastery_multiplier
    
    # Hermit bonus (implemented in status.py separately for HP/Vit)
    
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