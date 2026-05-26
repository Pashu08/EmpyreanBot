"""
backend/cultivation_helpers.py - Helper functions for Cultivation cog
"""

import random
import datetime
from typing import Dict, List, Tuple, Optional

from backend.constants import RANKS, ITEM_MUTATIONS
from backend.helpers import get_max_stats, get_next_rank
from backend.db import update_user_stat, add_item, update_item_name, has_item, remove_item, get_user_stat

print("[DEBUG] cultivation_helpers.py: Loading cultivation helpers...")


# ==========================================
# CONSTANTS (Balanced)
# ==========================================

# Minor realm progression order
MINOR_REALMS = ["Initial", "Early", "Middle", "Late", "Peak"]

# Ki requirements for each minor realm (% of max Ki cap)
MINOR_REALM_KI_REQUIREMENTS = {
    "Initial": 0,
    "Early": 15,    # 15% of max Ki
    "Middle": 35,   # 35% of max Ki
    "Late": 60,     # 60% of max Ki
    "Peak": 85,     # 85% of max Ki
}

# Minor breakthrough base chances (%) by rank and target realm
MINOR_BREAKTHROUGH_CHANCES = {
    "The Bound (Mortal)": {"Early": 85, "Middle": 70, "Late": 55, "Peak": 40},
    "Third-Rate Warrior": {"Early": 80, "Middle": 65, "Late": 50, "Peak": 35},
    "Second-Rate Warrior": {"Early": 75, "Middle": 60, "Late": 45, "Peak": 30},
    "First-Rate Warrior": {"Early": 70, "Middle": 55, "Late": 40, "Peak": 25},
    "Peak Master": {"Early": 65, "Middle": 50, "Late": 35, "Peak": 20},
}

# Major breakthrough base chances (%)
MAJOR_BREAKTHROUGH_CHANCES = {
    "The Bound (Mortal)": 35,
    "Third-Rate Warrior": 30,
    "Second-Rate Warrior": 25,
    "First-Rate Warrior": 20,
}

# Permanent bonuses for reaching minor realms
MINOR_REALM_BONUSES = {
    "Early": {"ki_gain": 2, "tech_damage": 0, "major_bt_chance": 0},
    "Middle": {"ki_gain": 4, "tech_damage": 2, "major_bt_chance": 0},
    "Late": {"ki_gain": 7, "tech_damage": 4, "major_bt_chance": 0},
    "Peak": {"ki_gain": 10, "tech_damage": 6, "major_bt_chance": 5},
}

# Failure penalties for minor breakthroughs
FAILURE_PENALTIES = {
    "Early": {"ki_percent": 10, "taels": 0},
    "Middle": {"ki_percent": 15, "taels": 20},
    "Late": {"ki_percent": 20, "taels": 30},
    "Peak": {"ki_percent": 25, "taels": 50},
}

# Major breakthrough failure penalty
MAJOR_FAILURE_PENALTY = {"ki_percent": 30, "taels": 100, "meridian_minutes": 15}

# Cooldowns (in minutes)
MINOR_COOLDOWN_MINUTES = 10
MAJOR_COOLDOWN_MINUTES = 30

# Major breakthrough stage choices
MAJOR_BREAKTHROUGH_STAGES = [
    {
        "name": "The Gathering",
        "description": "Your Ki is swirling violently within your dantian. It feels like molten lead.",
        "choices": [
            {"text": "Force it down", "base_success": 40, "bonus_effect": None},
            {"text": "Circulate slowly", "base_success": 60, "bonus_effect": None},
            {"text": "Let it overflow", "base_success": 20, "bonus_effect": "double_rewards"},
        ]
    },
    {
        "name": "The Core Heat",
        "description": "Your veins begin to glow. The heat is becoming unbearable.",
        "choices": [
            {"text": "Focus on breathing", "base_success": 50, "bonus_effect": "next_stage_boost"},
            {"text": "Ice the spirit", "base_success": 40, "bonus_effect": "heal"},
            {"text": "Endure the pain", "base_success": 60, "bonus_effect": "final_chance_boost"},
        ]
    },
    {
        "name": "The Final Wall",
        "description": "You see the bottleneck. A massive wall blocking your path.",
        "choices": [
            {"text": "All-out strike", "base_success": 40, "bonus_effect": None},
            {"text": "Look for a crack", "base_success": 50, "bonus_effect": None},
            {"text": "Pray for luck", "base_success": 30, "bonus_effect": "crit_success"},
        ]
    }
]


# ==========================================
# MINOR REALM HELPERS
# ==========================================

def get_minor_realm_from_ki(ki: int, max_ki_cap: int) -> str:
    """
    Determine current minor realm based on Ki percentage.
    
    Args:
        ki: Current Ki amount
        max_ki_cap: Maximum Ki cap for current rank
        
    Returns:
        str: Current minor realm (Initial, Early, Middle, Late, Peak)
    """
    if max_ki_cap <= 0:
        return "Initial"
    
    percentage = (ki / max_ki_cap) * 100
    
    for realm in reversed(MINOR_REALMS):
        required_pct = MINOR_REALM_KI_REQUIREMENTS.get(realm, 0)
        if percentage >= required_pct:
            return realm
    
    return "Initial"


def get_next_minor_realm(current_realm: str) -> Optional[str]:
    """
    Get the next minor realm after the current one.
    
    Args:
        current_realm: Current minor realm
        
    Returns:
        str or None: Next realm, or None if at Peak
    """
    if current_realm not in MINOR_REALMS:
        return "Early"
    
    current_index = MINOR_REALMS.index(current_realm)
    if current_index >= len(MINOR_REALMS) - 1:
        return None
    
    return MINOR_REALMS[current_index + 1]


def get_ki_required_for_minor_realm(target_realm: str, max_ki_cap: int) -> int:
    """
    Get Ki required to attempt breakthrough to a target minor realm.
    
    Args:
        target_realm: Target minor realm (Early, Middle, Late, Peak)
        max_ki_cap: Maximum Ki cap for current rank
        
    Returns:
        int: Ki required
    """
    required_pct = MINOR_REALM_KI_REQUIREMENTS.get(target_realm, 50)
    return int(max_ki_cap * required_pct / 100)


# ==========================================
# BREAKTHROUGH CHANCE CALCULATIONS
# ==========================================

async def get_minor_breakthrough_chance(
    db,
    user_id: int,
    rank: str,
    target_minor: str,
    current_ki: int,
    required_ki: int,
    has_pill: bool = False
) -> int:
    """
    Calculate the success chance for a minor breakthrough.
    
    Factors:
    - Base chance from rank and target realm
    - Laborer background: +5%
    - Extra Ki beyond requirement: up to +20%
    - Breakthrough Pill: +15%
    
    Returns:
        int: Success chance (0-95)
    """
    # Base chance
    realm_chances = MINOR_BREAKTHROUGH_CHANCES.get(rank, MINOR_BREAKTHROUGH_CHANCES["The Bound (Mortal)"])
    base_chance = realm_chances.get(target_minor, 50)
    
    # Background bonus
    bg = await get_user_stat(db, user_id, "background") or ""
    if bg == "Laborer":
        base_chance += 5
    
    # Extra Ki bonus (up to +20%)
    if current_ki > required_ki:
        extra_percent = (current_ki - required_ki) / required_ki * 100
        extra_bonus = min(20, int(extra_percent / 10) * 2)
        base_chance += extra_bonus
    
    # Pill bonus
    if has_pill:
        base_chance += 15
    
    # Permanent BT bonus from previous breakthroughs
    bt_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_bt") or 0
    base_chance += bt_bonus
    
    # Cap at 95%
    return min(base_chance, 95)


async def get_major_breakthrough_chance(
    db,
    user_id: int,
    rank: str,
    current_ki: int,
    required_ki: int,
    has_pill: bool = False
) -> int:
    """
    Calculate the success chance for a major breakthrough.
    
    Returns:
        int: Success chance (0-95)
    """
    # Base chance
    base_chance = MAJOR_BREAKTHROUGH_CHANCES.get(rank, 25)
    
    # Extra Ki bonus (up to +20%)
    if current_ki > required_ki:
        extra_percent = (current_ki - required_ki) / required_ki * 100
        extra_bonus = min(20, int(extra_percent / 10) * 2)
        base_chance += extra_bonus
    
    # Pill bonus
    if has_pill:
        base_chance += 15
    
    # Permanent BT bonus from minor breakthroughs
    bt_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_bt") or 0
    base_chance += bt_bonus
    
    # Cap at 95%
    return min(base_chance, 95)


# ==========================================
# BREAKTHROUGH APPLICATION
# ==========================================

async def apply_minor_success(
    db,
    user_id: int,
    target_minor: str
) -> Dict[str, int]:
    """
    Apply the effects of a successful minor breakthrough.
    
    Returns:
        dict: Bonuses gained (ki_gain, tech_damage, major_bt_chance)
    """
    # Update minor realm in database
    await update_user_stat(db, user_id, "minor_realm", target_minor)
    
    # Get bonuses for this realm
    bonus = MINOR_REALM_BONUSES.get(target_minor, {})
    ki_bonus = bonus.get("ki_gain", 0)
    damage_bonus = bonus.get("tech_damage", 0)
    bt_bonus = bonus.get("major_bt_chance", 0)
    
    # Update cumulative bonuses
    current_ki_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_ki") or 0
    current_damage_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_damage") or 0
    current_bt_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_bt") or 0
    
    await update_user_stat(db, user_id, "minor_breakthrough_bonus_ki", current_ki_bonus + ki_bonus)
    await update_user_stat(db, user_id, "minor_breakthrough_bonus_damage", current_damage_bonus + damage_bonus)
    await update_user_stat(db, user_id, "minor_breakthrough_bonus_bt", current_bt_bonus + bt_bonus)
    
    return {"ki_gain": ki_bonus, "tech_damage": damage_bonus, "major_bt_chance": bt_bonus}


async def apply_minor_failure(
    db,
    user_id: int,
    target_minor: str
) -> Tuple[int, int]:
    """
    Apply the effects of a failed minor breakthrough.
    
    Returns:
        tuple: (ki_lost_percent, taels_lost)
    """
    penalty = FAILURE_PENALTIES.get(target_minor, {"ki_percent": 15, "taels": 20})
    
    # Apply Ki loss
    current_ki = await get_user_stat(db, user_id, "ki") or 0
    new_ki = max(0, int(current_ki * (100 - penalty["ki_percent"]) / 100))
    await update_user_stat(db, user_id, "ki", new_ki)
    
    # Apply Taels loss
    if penalty["taels"] > 0:
        current_taels = await get_user_stat(db, user_id, "taels") or 0
        new_taels = max(0, current_taels - penalty["taels"])
        await update_user_stat(db, user_id, "taels", new_taels)
    
    return penalty["ki_percent"], penalty["taels"]


async def apply_major_success(
    db,
    user_id: int,
    current_rank: str,
    current_item: str
) -> Dict[str, any]:
    """
    Apply the effects of a successful major breakthrough.
    
    Returns:
        dict: New rank, new item, and stat caps
    """
    new_rank = get_next_rank(current_rank)
    target_stats = get_max_stats(new_rank)
    
    new_hp_cap = target_stats["max_hp"]
    new_vit_cap = target_stats["max_vit"]
    new_ki_cap = target_stats["ki_cap"]
    
    # Evolve item
    new_item = ITEM_MUTATIONS.get(current_item, current_item)
    try:
        await update_item_name(db, user_id, current_item, new_item)
    except Exception:
        await add_item(db, user_id, new_item, 1, bound=True)
    
    new_rank_id = RANKS.index(new_rank) if new_rank in RANKS else 0
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "rank": new_rank,
            "rank_id": new_rank_id,
            "minor_realm": "Initial",
            "item_id": new_item,
            "ki": 0,
            "hp": new_hp_cap,
            "vitality": new_vit_cap
        }}
    )
    
    return {
        "new_rank": new_rank,
        "new_item": new_item,
        "new_hp_cap": new_hp_cap,
        "new_vit_cap": new_vit_cap,
        "new_ki_cap": new_ki_cap
    }


async def apply_major_failure(
    db,
    user_id: int
) -> Tuple[int, int, int]:
    """
    Apply the effects of a failed major breakthrough.
    
    Returns:
        tuple: (ki_lost_percent, taels_lost, meridian_minutes)
    """
    penalty = MAJOR_FAILURE_PENALTY
    
    # Apply Ki loss
    current_ki = await get_user_stat(db, user_id, "ki") or 0
    new_ki = max(0, int(current_ki * (100 - penalty["ki_percent"]) / 100))
    await update_user_stat(db, user_id, "ki", new_ki)
    
    # Apply Taels loss
    current_taels = await get_user_stat(db, user_id, "taels") or 0
    new_taels = max(0, current_taels - penalty["taels"])
    await update_user_stat(db, user_id, "taels", new_taels)
    
    # Apply meridian damage
    debuff_time = (datetime.datetime.now() + datetime.timedelta(minutes=penalty["meridian_minutes"])).isoformat()
    await update_user_stat(db, user_id, "meridian_damage", debuff_time)
    
    return penalty["ki_percent"], penalty["taels"], penalty["meridian_minutes"]


# ==========================================
# MAJOR BREAKTHROUGH STAGE HELPERS
# ==========================================

def get_major_stage(stage_index: int) -> Dict:
    """
    Get data for a specific major breakthrough stage.
    
    Args:
        stage_index: 0, 1, or 2
        
    Returns:
        dict: Stage data with name, description, and choices
    """
    if stage_index < len(MAJOR_BREAKTHROUGH_STAGES):
        return MAJOR_BREAKTHROUGH_STAGES[stage_index].copy()
    return MAJOR_BREAKTHROUGH_STAGES[-1].copy()


def calculate_stage_success(
    stage_index: int,
    choice_index: int,
    previous_boost: bool = False
) -> Tuple[bool, int, Dict]:
    """
    Calculate success for a major breakthrough stage.
    
    Args:
        stage_index: Current stage (0, 1, 2)
        choice_index: Which choice was selected (0, 1, 2)
        previous_boost: Whether previous stage gave a boost
        
    Returns:
        tuple: (success, success_chance, effects)
    """
    stage = MAJOR_BREAKTHROUGH_STAGES[stage_index]
    choice = stage["choices"][choice_index]
    
    base_success = choice["base_success"]
    
    # Apply previous boost
    if previous_boost:
        base_success += 10
    
    # Random roll
    roll = random.randint(1, 100)
    success = roll <= base_success
    
    effects = {
        "next_stage_boost": False,
        "heal_amount": 0,
        "final_chance_boost": False,
        "double_rewards": False,
        "crit_success": False
    }
    
    # Apply special effects
    bonus_effect = choice.get("bonus_effect")
    if bonus_effect == "next_stage_boost":
        effects["next_stage_boost"] = True
    elif bonus_effect == "heal" and success:
        effects["heal_amount"] = 20
    elif bonus_effect == "final_chance_boost" and success:
        effects["final_chance_boost"] = True
    elif bonus_effect == "double_rewards" and success:
        effects["double_rewards"] = True
    elif bonus_effect == "crit_success" and success and roll <= 10:
        effects["crit_success"] = True
    
    return success, base_success, effects


async def finalize_major_breakthrough(
    db,
    user_id: int,
    current_rank: str,
    current_item: str,
    stage_results: List[bool],
    stage_effects: List[Dict]
) -> Dict:
    """
    Finalize major breakthrough after all stages.
    
    Args:
        db: Database connection
        user_id: User ID
        current_rank: Current rank
        current_item: Current item
        stage_results: List of success/failure per stage
        stage_effects: List of effects per stage
        
    Returns:
        dict: Breakthrough result (success, rewards, or failure details)
    """
    # Check if all stages succeeded
    all_succeeded = all(stage_results)
    
    # Check for crit success (overrides failure)
    crit_success = any(effects.get("crit_success", False) for effects in stage_effects)
    
    if all_succeeded or crit_success:
        # Apply major success
        result = await apply_major_success(db, user_id, current_rank, current_item)
        
        # Double rewards if applicable
        double_rewards = any(effects.get("double_rewards", False) for effects in stage_effects)
        if double_rewards and result.get("new_item"):
            await add_item(db, user_id, result["new_item"], 1, bound=True)
            result["double_reward"] = True
        
        return {"success": True, **result}
    else:
        # Apply major failure
        ki_loss, tael_loss, meridian_minutes = await apply_major_failure(db, user_id)
        return {
            "success": False,
            "ki_loss_percent": ki_loss,
            "tael_loss": tael_loss,
            "meridian_minutes": meridian_minutes
        }


print("[DEBUG] cultivation_helpers.py: Cultivation helpers loaded successfully")