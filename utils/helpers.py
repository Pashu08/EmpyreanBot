"""
helpers.py - Shared utility functions for Empyrean Bot
All cogs should import from here instead of duplicating code.
"""

import datetime
import random
from utils.constants import RANK_STATS, BREAKTHROUGH_KI, MURIM_EVENTS, FACTIONS

print("[DEBUG] helpers.py: Loading helper functions...")

# ==========================================
# EXISTING FUNCTIONS (with debug prints)
# ==========================================

def get_rank_index(rank_name: str) -> int:
    """Convert rank name to index number (0-4)."""
    print(f"[DEBUG] helpers.get_rank_index: rank_name={rank_name}")
    rank_map = {
        "The Bound (Mortal)": 0,
        "Third-Rate Warrior": 1,
        "Second-Rate Warrior": 2,
        "First-Rate Warrior": 3,
        "Peak Master": 4
    }
    result = rank_map.get(rank_name, 0)
    print(f"[DEBUG] helpers.get_rank_index: result={result}")
    return result

def get_rank_from_ki(ki_amount: int) -> str:
    """Determine what rank a user should be based on Ki amount."""
    print(f"[DEBUG] helpers.get_rank_from_ki: ki_amount={ki_amount}")
    if ki_amount >= 15000:
        result = "Peak Master"
    elif ki_amount >= 7500:
        result = "First-Rate Warrior"
    elif ki_amount >= 3000:
        result = "Second-Rate Warrior"
    elif ki_amount >= 1000:
        result = "Third-Rate Warrior"
    else:
        result = "The Bound (Mortal)"
    print(f"[DEBUG] helpers.get_rank_from_ki: result={result}")
    return result

def get_max_stats(rank_name: str) -> dict:
    """Get max HP, Vitality, and Ki cap for a rank."""
    print(f"[DEBUG] helpers.get_max_stats: rank_name={rank_name}")
    stats = RANK_STATS.get(rank_name, RANK_STATS["The Bound (Mortal)"])
    result = {
        "max_hp": stats["hp_cap"],
        "max_vit": stats["vit_cap"],
        "ki_cap": stats["ki_cap"]
    }
    print(f"[DEBUG] helpers.get_max_stats: caps={result}")
    return result

def get_breakthrough_ki_required(current_rank: str, background: str = None) -> int:
    """Get Ki required for breakthrough, with Laborer discount."""
    print(f"[DEBUG] helpers.get_breakthrough_ki_required: rank={current_rank}, bg={background}")
    from utils.constants import BREAKTHROUGH_KI

    required = BREAKTHROUGH_KI.get(current_rank, 100)

    if background == "Laborer":
        required = int(required * 0.85)
        print(f"[DEBUG] helpers.get_breakthrough_ki_required: Laborer discount applied, new={required}")

    print(f"[DEBUG] helpers.get_breakthrough_ki_required: required={required}")
    return required

def get_next_rank(current_rank: str) -> str:
    """Get the next rank name after breakthrough."""
    print(f"[DEBUG] helpers.get_next_rank: current={current_rank}")
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
            result = rank_order[current_index + 1]
            print(f"[DEBUG] helpers.get_next_rank: next={result}")
            return result
    except ValueError:
        pass

    print(f"[DEBUG] helpers.get_next_rank: no next rank, staying at {current_rank}")
    return current_rank

def calculate_afk_gains(rank: str, hours_passed: float, profession: str = None, background: str = None) -> dict:
    """Calculate Ki and Mastery gained while offline."""
    print(f"[DEBUG] helpers.calculate_afk_gains: rank={rank}, hours={hours_passed}, prof={profession}, bg={background}")
    from utils.constants import AFK_KI_PER_HOUR, AFK_MASTERY_PER_HOUR

    ki_rate = AFK_KI_PER_HOUR.get(rank, 150)
    ki_gained = int(ki_rate * hours_passed)

    mastery_multiplier = 1.15 if profession == "Instructor" else 1.0
    mastery_gained = AFK_MASTERY_PER_HOUR * hours_passed * mastery_multiplier

    result = {
        "ki": ki_gained,
        "mastery": mastery_gained
    }
    print(f"[DEBUG] helpers.calculate_afk_gains: ki_gained={ki_gained}, mastery_gained={mastery_gained}")
    return result

def calculate_stage_from_ki(ki: int, ki_cap: int) -> str:
    """Determine cultivation stage based on current Ki vs cap."""
    print(f"[DEBUG] helpers.calculate_stage_from_ki: ki={ki}, cap={ki_cap}")
    from utils.constants import STAGES

    if ki >= ki_cap:
        result = "Peak"
    elif ki >= ki_cap * 0.75:
        result = "Late"
    elif ki >= ki_cap * 0.50:
        result = "Middle"
    else:
        result = "Initial"
    print(f"[DEBUG] helpers.calculate_stage_from_ki: stage={result}")
    return result

def has_meridian_damage(meridian_damage_str) -> tuple:
    """Check if user has active meridian damage. Returns (is_damaged, minutes_remaining)."""
    print(f"[DEBUG] helpers.has_meridian_damage: input={meridian_damage_str}")
    if not meridian_damage_str:
        print(f"[DEBUG] helpers.has_meridian_damage: no damage")
        return (False, 0)

    try:
        exp_time = datetime.datetime.fromisoformat(meridian_damage_str)
        now = datetime.datetime.now()
        if now < exp_time:
            diff = exp_time - now
            minutes = int(diff.total_seconds() // 60)
            print(f"[DEBUG] helpers.has_meridian_damage: damaged, {minutes} minutes left")
            return (True, minutes)
    except (ValueError, TypeError):
        pass

    print(f"[DEBUG] helpers.has_meridian_damage: no active damage")
    return (False, 0)

# ==========================================
# NEW HELPER FUNCTIONS
# ==========================================

# --- Faction reputation (using FACTIONS from constants) ---
def get_faction_reputation(user_data: dict, faction_name: str) -> int:
    """
    Get a user's reputation with a specific faction.
    user_data should contain a 'faction_reputations' dict (or we can add a column later).
    For now, returns starting reputation from constants if no data found.
    """
    print(f"[DEBUG] helpers.get_faction_reputation: faction={faction_name}")
    # This is a placeholder – you will need to add a 'faction_reputations' column to users table
    # or create a separate table. For now, return default starting rep.
    faction_info = FACTIONS.get(faction_name, {})
    default = faction_info.get("starting_reputation", 0)
    print(f"[DEBUG] helpers.get_faction_reputation: default={default}")
    return default

def add_faction_reputation(user_data: dict, faction_name: str, amount: int) -> dict:
    """
    Add or subtract reputation from a faction.
    Returns updated user_data (placeholder – actual DB update required elsewhere).
    """
    print(f"[DEBUG] helpers.add_faction_reputation: faction={faction_name}, amount={amount}")
    # Placeholder – you will implement actual database update when adding faction system
    print(f"[DEBUG] helpers.add_faction_reputation: would add {amount} to {faction_name}")
    return user_data

# --- Random Murim event (from constants.MURIM_EVENTS) ---
def roll_random_event(return_effects_only: bool = False):
    """
    Return a random Murim event from constants.MURIM_EVENTS.
    If return_effects_only is True, returns (description, effects_dict).
    If False, returns (description, effects_dict) as well (same for now).
    """
    print(f"[DEBUG] helpers.roll_random_event: return_effects_only={return_effects_only}")
    event = random.choice(MURIM_EVENTS)
    description, effects = event
    print(f"[DEBUG] helpers.roll_random_event: event='{description[:50]}...'")
    return description, effects

# --- Embed color formatter (uses colors from constants) ---
def format_embed_color(color_name: str) -> int:
    """
    Convert a color name to a Discord hex value.
    Valid names: "main", "win", "lose", "gold", "teal"
    """
    from utils.constants import COLOR_MAIN, COLOR_WIN, COLOR_LOSE, COLOR_GOLD, COLOR_TEAL
    print(f"[DEBUG] helpers.format_embed_color: color_name={color_name}")
    colors = {
        "main": COLOR_MAIN,
        "win": COLOR_WIN,
        "lose": COLOR_LOSE,
        "gold": COLOR_GOLD,
        "teal": COLOR_TEAL,
    }
    result = colors.get(color_name.lower(), COLOR_MAIN)
    print(f"[DEBUG] helpers.format_embed_color: result={hex(result)}")
    return result

print("[DEBUG] helpers.py: Helper functions loaded successfully")