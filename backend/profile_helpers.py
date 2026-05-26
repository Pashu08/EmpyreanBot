"""
backend/profile_helpers.py - Helper functions for Profile cog

This module handles:
- Background data retrieval (perk, item, emoji)
- Daily bonus status calculation
- Mastery milestone progress calculation
- Hidden technique status detection
- Inventory summary generation
- Profession display formatting
"""

import datetime
from typing import Tuple, Optional, Dict, Any

from backend.constants import BACKGROUNDS, TECHNIQUES

print("[DEBUG] profile_helpers.py: Loading profile helpers...")


# ==========================================
# BACKGROUND HELPERS
# ==========================================

def get_background_emoji(background_name: str) -> str:
    """
    Get the emoji for a background.
    
    Args:
        background_name: Name of the background (Laborer, Outcast, Hermit)
        
    Returns:
        str: Emoji for the background, or default emoji if not found
    """
    bg_data = BACKGROUNDS.get(background_name, {})
    return bg_data.get("emoji", "📜")


def get_background_perk(background_name: str) -> str:
    """
    Get the perk description for a background.
    
    Args:
        background_name: Name of the background
        
    Returns:
        str: Perk description
    """
    bg_data = BACKGROUNDS.get(background_name, {})
    return bg_data.get("perk", "No special perk.")


def get_background_item(background_name: str) -> str:
    """
    Get the starting item for a background.
    
    Args:
        background_name: Name of the background
        
    Returns:
        str: Starting item name
    """
    bg_data = BACKGROUNDS.get(background_name, {})
    return bg_data.get("item", "Unknown item")


# ==========================================
# DAILY BONUS HELPERS
# ==========================================

def get_daily_bonus_status(user_data: Dict[str, Any]) -> Tuple[bool, bool, int, int]:
    """
    Calculate daily bonus availability for work and observe.
    
    Args:
        user_data: User document from database (contains daily_work_date, daily_observe_date)
        
    Returns:
        Tuple[bool, bool, int, int]: (work_available, observe_available, hours_until_reset, minutes_until_reset)
    """
    now = datetime.datetime.now()
    today = now.date().isoformat()
    
    work_date = user_data.get('daily_work_date')
    observe_date = user_data.get('daily_observe_date')
    
    work_available = work_date is None or work_date != today
    observe_available = observe_date is None or observe_date != today
    
    # Calculate time until next reset (midnight UTC)
    next_reset = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)
    reset_delta = next_reset - now
    
    hours = int(reset_delta.total_seconds() // 3600)
    minutes = int((reset_delta.total_seconds() % 3600) // 60)
    
    return work_available, observe_available, hours, minutes


# ==========================================
# MASTERY MILESTONE HELPERS
# ==========================================

def get_milestone_progress(technique: str, mastery_flags: Optional[str]) -> Tuple[int, int]:
    """
    Calculate how many milestones a user has reached for their technique.
    
    Milestones are at 25%, 50%, 75%, and 100% mastery.
    
    Args:
        technique: Name of the active technique (or "None")
        mastery_flags: Comma-separated string of milestone flags
        
    Returns:
        Tuple[int, int]: (milestones_reached, total_milestones)
        
    Example:
        >>> get_milestone_progress("Flowing Cloud Steps", "Flowing Cloud Steps:25,Flowing Cloud Steps:50")
        (2, 4)
    """
    if technique == "None":
        return 0, 0
    
    reached = []
    total_milestones = 4  # 25, 50, 75, 100
    
    if mastery_flags:
        try:
            for part in mastery_flags.split(","):
                if part.startswith(f"{technique}:"):
                    milestone = int(part.split(":")[1])
                    reached.append(milestone)
        except (ValueError, IndexError):
            pass
    
    return len(reached), total_milestones


def get_mastery_percentage(user_data: Dict[str, Any]) -> Optional[float]:
    """
    Get the mastery percentage for the user's active technique.
    
    Args:
        user_data: User document from database
        
    Returns:
        Optional[float]: Mastery percentage (0-100), or None if no technique
    """
    active_tech = user_data.get("active_tech", "None")
    if active_tech == "None":
        return None
    
    return user_data.get("mastery", 0.0)


# ==========================================
# HIDDEN TECHNIQUE HELPERS
# ==========================================

# Mapping of techniques to their hidden forms
HIDDEN_TECHNIQUE_MAP = {
    "Flowing Cloud Steps": "Flowing Cloud Shadow Step",
    "Swift Wind Kick": "Swift Hurricane Kick",
    "Golden Bell Shield": "Indestructible Diamond Body",
    "Vajra Guard Mantra": "Vajra Body Rebirth",
}


def get_hidden_technique_hint(technique: str, mastery_flags: Optional[str], milestones_reached: int) -> str:
    """
    Generate a mysterious hint about hidden technique progress.
    
    Args:
        technique: Name of the active technique
        mastery_flags: Comma-separated string of milestone flags
        milestones_reached: Number of milestones reached (0-4)
        
    Returns:
        str: Hint text about hidden technique
    """
    if technique == "None":
        return "No technique selected"
    
    # Check if already unlocked (100% mastery)
    if mastery_flags and f"{technique}:100" in mastery_flags.split(","):
        hidden_name = HIDDEN_TECHNIQUE_MAP.get(technique, "a forgotten art")
        return f"✨ **{hidden_name}** (Awakened!)"
    
    # Progress-based hints
    if milestones_reached >= 3:
        return "🌟 *The final seal trembles... complete mastery awaits*"
    elif milestones_reached >= 2:
        return "🔓 *You sense a deeper power locked within*"
    elif milestones_reached >= 1:
        return "🔒 *Whispers of a hidden form echo in your mind*"
    else:
        return "❓ *The true depth of this technique remains hidden*"


# ==========================================
# INVENTORY HELPERS
# ==========================================

async def get_inventory_summary(db, user_id: int) -> Tuple[int, int]:
    """
    Get a summary of a user's inventory.
    
    Args:
        db: MongoDB wrapper instance
        user_id: Discord user ID
        
    Returns:
        Tuple[int, int]: (total_quantity, unique_items)
    """
    total_qty = 0
    unique_count = 0
    
    try:
        cursor = db.inventory.find({"user_id": user_id})
        items = await cursor.to_list(length=100)
        
        for item in items:
            total_qty += item.get("quantity", 0)
            unique_count += 1
    except Exception:
        pass
    
    return total_qty, unique_count


# ==========================================
# PROFESSION HELPERS
# ==========================================

def get_profession_display(profession: str, rank: str) -> str:
    """
    Format profession name with rank for display.
    
    Args:
        profession: Profession name (e.g., "Alchemist")
        rank: Rank (e.g., "Apprentice")
        
    Returns:
        str: Formatted profession string
    """
    if not profession or profession == "None":
        return "None"
    
    return f"{profession} ({rank})"


# ==========================================
# TECHNIQUE DISPLAY HELPERS
# ==========================================

def get_technique_display_name(technique: str) -> str:
    """
    Get the display name for a technique (with emoji if available).
    
    Args:
        technique: Technique name
        
    Returns:
        str: Display name with emoji
    """
    if technique == "None":
        return "None"
    
    tech_data = TECHNIQUES.get(technique, {})
    emoji = tech_data.get("emoji", "📜")
    
    return f"{emoji} {technique}"


print("[DEBUG] profile_helpers.py: Profile helpers loaded successfully")