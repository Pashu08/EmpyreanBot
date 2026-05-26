"""
backend/combat_helpers.py - Combat helper functions for the hunting system

This module provides:
- Health bar generation
- Damage calculation (normal attacks, techniques, critical hits)
- Enemy rarity selection (Common → Mythical)
- Enemy name generation based on rank and rarity
- Reward calculation with multipliers (rarity, daily bonus, combat mastery)
- Technique effect processing (dodge boost, double strike, damage reduction, HP regen)
"""

import random
from typing import Tuple, Dict, Any, Optional

# Import constants from the central constants file
from backend.constants import RANK_STATS, TECHNIQUES

print("[DEBUG] combat_helpers.py: Loading combat helpers...")


# ==========================================
# RARITY SYSTEM (5 tiers)
# ==========================================

# Rarity definitions with their modifiers
# Used for enemy scaling and rewards
RARITIES = {
    "Common": {
        "chance": 45,           # 45% chance to spawn
        "hp_mult": 1.0,        # Normal HP
        "atk_mult": 1.0,       # Normal attack
        "reward_mult": 1.0,    # Normal reward
        "drop_chance": 0.05,   # 5% chance for item drop
        "emoji": "⚪"           # White circle for Common
    },
    "Elite": {
        "chance": 25,           # 25% chance to spawn
        "hp_mult": 1.5,        # 50% more HP
        "atk_mult": 1.5,       # 50% more attack
        "reward_mult": 1.5,    # 50% more reward
        "drop_chance": 0.15,   # 15% chance for item drop
        "emoji": "🟢"           # Green for Elite
    },
    "Master": {
        "chance": 15,           # 15% chance to spawn
        "hp_mult": 2.2,        # 120% more HP
        "atk_mult": 2.2,       # 120% more attack
        "reward_mult": 2.2,    # 120% more reward
        "drop_chance": 0.30,   # 30% chance for item drop
        "emoji": "🔵"           # Blue for Master
    },
    "Grandmaster": {
        "chance": 10,           # 10% chance to spawn
        "hp_mult": 3.0,        # 200% more HP
        "atk_mult": 3.0,       # 200% more attack
        "reward_mult": 3.0,    # 200% more reward
        "drop_chance": 0.50,   # 50% chance for item drop
        "emoji": "🟣"           # Purple for Grandmaster
    },
    "Mythical": {
        "chance": 5,            # 5% chance to spawn (rare!)
        "hp_mult": 4.5,        # 350% more HP
        "atk_mult": 4.5,       # 350% more attack
        "reward_mult": 4.5,    # 350% more reward
        "drop_chance": 0.80,   # 80% chance for item drop
        "emoji": "🔴"           # Red for Mythical (boss)
    }
}

# Murim-style enemy names by rank and rarity
ENEMY_NAMES = {
    "Third-Rate Warrior": {
        "Common": "Blood Wolf",
        "Elite": "Shadow Wolf Pack Leader",
        "Master": "Frost Wolf King",
        "Grandmaster": "Moonlight Devourer",
        "Mythical": "Fenrir, The World-Ender"
    },
    "Second-Rate Warrior": {
        "Common": "Ironhide Panther",
        "Elite": "Venomous Shadow Panther",
        "Master": "Ember Mane Panther",
        "Grandmaster": "Star-Swallowing Panther",
        "Mythical": "Asura, The Soul Reaper"
    },
    "First-Rate Warrior": {
        "Common": "Corrupted Monk",
        "Elite": "Fallen Elder",
        "Master": "Soul Devouring Monk",
        "Grandmaster": "Heaven Defier",
        "Mythical": "Primordial Demon Lord"
    },
    "Peak Master": {
        "Common": "Ancient Bloodfiend",
        "Elite": "Crimson Blood Count",
        "Master": "Scarlet King",
        "Grandmaster": "Blood Emperor",
        "Mythical": "Kami of Eternal Night"
    }
}


# ==========================================
# HEALTH BAR
# ==========================================

def generate_health_bar(current: int, max_hp: int) -> str:
    """
    Generate a visual health bar using red and black squares.
    
    Args:
        current: Current HP value
        max_hp: Maximum HP value
        
    Returns:
        str: Health bar string (e.g., "🟥🟥🟥⬛⬛⬛⬛⬛⬛⬛")
        
    Example:
        >>> generate_health_bar(75, 100)
        '🟥🟥🟥🟥🟥🟥🟥⬛⬛⬛'
    """
    # Calculate ratio (0.0 to 1.0)
    ratio = max(0.0, min(current / max_hp, 1.0))
    
    # Convert ratio to number of filled squares (0-10)
    filled = int(ratio * 10)
    
    # Build the bar: filled red squares + empty black squares
    return "🟥" * filled + "⬛" * (10 - filled)


# ==========================================
# ATTACK VALUE GETTERS
# ==========================================

def get_rank_attack(rank: str) -> int:
    """
    Get the base attack value for a player's rank.
    
    Args:
        rank: Player's rank string (e.g., "Third-Rate Warrior")
        
    Returns:
        int: Base attack value for normal strikes
        
    Example:
        >>> get_rank_attack("Third-Rate Warrior")
        25
    """
    rank_stats = RANK_STATS.get(rank, RANK_STATS["The Bound (Mortal)"])
    return rank_stats.get("atk", 10)


def get_technique_attack(rank: str) -> int:
    """
    Get the technique attack value for a player's rank.
    
    Technique attacks are stronger than normal strikes.
    
    Args:
        rank: Player's rank string
        
    Returns:
        int: Base technique attack value
        
    Example:
        >>> get_technique_attack("Third-Rate Warrior")
        50
    """
    rank_stats = RANK_STATS.get(rank, RANK_STATS["The Bound (Mortal)"])
    return rank_stats.get("tech_atk", 20)


# ==========================================
# DAMAGE CALCULATION
# ==========================================

def calculate_normal_damage(base_attack: int, variance: int = 25) -> Tuple[int, bool]:
    """
    Calculate damage for a normal strike.
    
    Args:
        base_attack: Base attack value from player's rank
        variance: Random variance range (default 25)
        
    Returns:
        Tuple[int, bool]: (damage, was_critical)
        
    Example:
        >>> calculate_normal_damage(25)
        (37, False)  # 25 + random(0-25)
    """
    # Base damage + random variance
    damage = random.randint(base_attack, base_attack + variance)
    
    # 10% critical hit chance
    is_critical = random.random() < 0.1
    if is_critical:
        damage *= 2
    
    return damage, is_critical


def calculate_technique_damage(
    base_attack: int,
    mastery: float,
    variance: int = 50
) -> Tuple[int, bool]:
    """
    Calculate damage for a technique strike.
    
    Technique damage scales with mastery percentage.
    
    Args:
        base_attack: Base technique attack from player's rank
        mastery: Technique mastery percentage (0-100)
        variance: Random variance range (default 50)
        
    Returns:
        Tuple[int, bool]: (damage, was_critical)
        
    Example:
        >>> calculate_technique_damage(50, 75.5)
        (132, False)  # (50 + random(0-50)) * (1 + 0.755)
    """
    # Base damage + random variance
    base_damage = random.randint(base_attack, base_attack + variance)
    
    # Mastery multiplier (e.g., 75% mastery = 1.75x damage)
    mastery_multiplier = 1 + (mastery / 100)
    damage = int(base_damage * mastery_multiplier)
    
    # 10% critical hit chance
    is_critical = random.random() < 0.1
    if is_critical:
        damage *= 2
    
    return damage, is_critical


def calculate_enemy_damage(
    enemy_attack: int,
    player_technique: str,
    variance: int = 10
) -> int:
    """
    Calculate damage dealt by the enemy.
    
    Damage is reduced if player has Golden Bell Shield technique.
    
    Args:
        enemy_attack: Enemy's base attack value
        player_technique: Player's equipped technique name
        variance: Random variance range (default 10)
        
    Returns:
        int: Final damage dealt to player
        
    Example:
        >>> calculate_enemy_damage(45, "Golden Bell Shield")
        36  # 45 with 20% reduction
    """
    # Enemy damage has slight randomness
    damage = random.randint(
        max(1, enemy_attack - variance),
        enemy_attack + variance
    )
    
    # Apply technique damage reduction if applicable
    if player_technique == "Golden Bell Shield":
        damage = int(damage * 0.8)  # 20% damage reduction
    
    return max(1, damage)  # Minimum 1 damage


# ==========================================
# ENCOUNTER GENERATION
# ==========================================

def choose_enemy_rarity() -> Tuple[str, Dict]:
    """
    Randomly choose an enemy rarity based on spawn chances.
    
    Returns:
        Tuple[str, Dict]: (rarity_name, rarity_data)
        
    Example:
        >>> rarity_name, rarity_data = choose_enemy_rarity()
        >>> print(rarity_name)
        'Elite'
    """
    # Generate random number 1-100
    roll = random.randint(1, 100)
    
    cumulative = 0
    for rarity_name, rarity_data in RARITIES.items():
        cumulative += rarity_data["chance"]
        if roll <= cumulative:
            # Return a copy to avoid modifying the original
            return rarity_name, rarity_data.copy()
    
    # Fallback to Common (should never happen)
    return "Common", RARITIES["Common"].copy()


def get_enemy_name(base_rank: str, rarity: str) -> str:
    """
    Get the flavored enemy name based on rank and rarity.
    
    Args:
        base_rank: Player's rank (determines enemy tier)
        rarity: Rarity name (Common, Elite, etc.)
        
    Returns:
        str: Enemy name with appropriate flavor
        
    Example:
        >>> get_enemy_name("Third-Rate Warrior", "Mythical")
        'Fenrir, The World-Ender'
    """
    tier_names = ENEMY_NAMES.get(base_rank, ENEMY_NAMES["Third-Rate Warrior"])
    return tier_names.get(rarity, "Unknown Beast")


def generate_enemy(
    base_rank: str,
    player_rank: str = None
) -> Tuple[Dict, str, Dict]:
    """
    Generate a complete enemy with stats and rarity.
    
    Args:
        base_rank: Base enemy tier (determines base stats)
        player_rank: Player's rank (for scaling, optional)
        
    Returns:
        Tuple[Dict, str, Dict]: (enemy_data, rarity_name, rarity_data)
        
    Example:
        >>> enemy, rarity, data = generate_enemy("Third-Rate Warrior")
        >>> print(enemy["name"])
        'Shadow Wolf Pack Leader'
    """
    from backend.constants import ENEMIES
    
    # Choose rarity
    rarity_name, rarity_data = choose_enemy_rarity()
    
    # Get enemy name
    enemy_name = get_enemy_name(base_rank, rarity_name)
    
    # Get base enemy stats from constants
    base_enemy = ENEMIES.get(base_rank, ENEMIES["Third-Rate Warrior"])
    
    # Apply rarity multipliers
    enemy_hp = int(base_enemy["hp"] * rarity_data["hp_mult"])
    enemy_atk = int(base_enemy["atk"] * rarity_data["atk_mult"])
    enemy_color = base_enemy["color"]
    
    enemy_data = {
        "name": enemy_name,
        "hp": enemy_hp,
        "max_hp": enemy_hp,
        "atk": enemy_atk,
        "color": enemy_color,
        "base_rank": base_rank
    }
    
    return enemy_data, rarity_name, rarity_data


# ==========================================
# REWARD CALCULATION
# ==========================================

def calculate_reward(
    base_reward_range: Tuple[int, int] = (50, 150),
    rarity_multiplier: float = 1.0,
    daily_bonus_active: bool = False,
    combat_mastery: float = 0
) -> int:
    """
    Calculate the final Taels reward for defeating an enemy.
    
    Formula: base_reward * rarity_mult * (2 if daily_bonus) * (1 + cm/200)
    
    Args:
        base_reward_range: Tuple of (min, max) for base reward
        rarity_multiplier: Multiplier based on enemy rarity
        daily_bonus_active: Whether player has daily bonus active (first 3 hunts)
        combat_mastery: Player's combat mastery stat (0-100)
        
    Returns:
        int: Final reward in Taels
        
    Example:
        >>> calculate_reward((50, 150), 2.2, True, 50)
        495  # 100 * 2.2 * 2 * 1.25
    """
    # Random base reward within range
    base_reward = random.randint(base_reward_range[0], base_reward_range[1])
    
    # Apply rarity multiplier
    reward = int(base_reward * rarity_multiplier)
    
    # Apply daily bonus (2x for first 3 hunts)
    if daily_bonus_active:
        reward *= 2
    
    # Apply combat mastery bonus (0.5% per point, max 50% bonus)
    cm_bonus = 1 + (combat_mastery * 0.005)
    final_reward = int(reward * cm_bonus)
    
    return final_reward


def calculate_tael_loss(current_taels: int, loss_percent: float = 0.10) -> int:
    """
    Calculate Taels lost when fleeing or being defeated.
    
    Args:
        current_taels: Player's current Taels
        loss_percent: Percentage to lose (default 10%)
        
    Returns:
        int: Amount of Taels to lose (minimum 1)
        
    Example:
        >>> calculate_tael_loss(500)
        50
    """
    loss = int(current_taels * loss_percent)
    return max(1, loss)  # Minimum loss of 1 Tael


# ==========================================
# TECHNIQUE EFFECT PROCESSING
# ==========================================

def process_technique_effect(
    technique_name: str,
    player_hp: int,
    player_max_hp: int,
    enemy_hp: int,
    damage_dealt: int
) -> Dict[str, Any]:
    """
    Process special technique effects (mastery milestones).
    
    Args:
        technique_name: Name of the technique used
        player_hp: Player's current HP
        player_max_hp: Player's maximum HP
        enemy_hp: Enemy's current HP
        damage_dealt: Damage dealt by the technique
        
    Returns:
        Dict with keys: extra_damage, heal_amount, effect_message
    """
    result = {
        "extra_damage": 0,
        "heal_amount": 0,
        "effect_message": ""
    }
    
    # Swift Wind Kick: 30% chance for double strike
    if technique_name == "Swift Wind Kick" and random.random() < 0.3:
        # Extra damage is half of the original
        extra_damage = damage_dealt // 2
        result["extra_damage"] = extra_damage
        result["effect_message"] = f"**Double strike!** +{extra_damage} damage!"
    
    # Vajra Guard Mantra: 5% HP regeneration
    elif technique_name == "Vajra Guard Mantra":
        heal = int(player_max_hp * 0.05)
        result["heal_amount"] = min(heal, player_max_hp - player_hp)
        if result["heal_amount"] > 0:
            result["effect_message"] = f"**Healing aura!** +{result['heal_amount']} HP restored!"
    
    # Flowing Cloud Steps: Dodge boost (handled in combat logic)
    # Golden Bell Shield: Damage reduction (handled in damage calculation)
    
    return result


# ==========================================
# LEADERBOARD HELPERS
# ==========================================

def format_leaderboard_value(value: int, mode: str) -> str:
    """
    Format a leaderboard value based on the mode.
    
    Args:
        value: The raw value from database
        mode: Leaderboard mode (total_hunts, fastest_kill, etc.)
        
    Returns:
        str: Formatted value string
    """
    if mode == "fastest_kill":
        return f"{value} turns"
    else:
        return str(value)


# ==========================================
# ENEMY TIER DETERMINATION
# ==========================================

def get_enemy_tier_from_player_rank(player_rank: str) -> Optional[str]:
    """
    Determine what enemy tier a player can face based on their rank.
    
    Mortals cannot hunt. Players fight enemies of their own rank.
    
    Args:
        player_rank: Player's cultivation rank
        
    Returns:
        str or None: Enemy tier name, or None if cannot hunt
        
    Example:
        >>> get_enemy_tier_from_player_rank("Third-Rate Warrior")
        'Third-Rate Warrior'
        >>> get_enemy_tier_from_player_rank("The Bound (Mortal)")
        None
    """
    if "Peak Master" in player_rank:
        return "Peak Master"
    elif "First-Rate" in player_rank:
        return "First-Rate Warrior"
    elif "Second-Rate" in player_rank:
        return "Second-Rate Warrior"
    elif "Third-Rate" in player_rank:
        return "Third-Rate Warrior"
    else:
        # Mortals cannot hunt
        return None


print("[DEBUG] combat_helpers.py: Combat helpers loaded successfully")