"""
embeds/combat_embeds.py - Embed designs for Combat cog
Contains all embed builders for hunting, combat, and leaderboards.

This file handles:
- Main combat battle embed (HP bars, combat log, turn info)
- Victory screen (rewards, drops, combat mastery gain)
- Defeat screen (tael loss, meridian damage)
- Flee screen (escape penalty, cooldown)
- Cooldown messages
- Leaderboard displays
"""

import discord
from backend.helpers import format_embed_color

print("[DEBUG] combat_embeds.py: Loading combat embeds...")


# ==========================================
# HEALTH BAR GENERATOR (moved from CombatView)
# ==========================================

def generate_health_bar(current: int, total: int) -> str:
    """
    Generate a visual health bar using emojis.
    
    Args:
        current: Current HP value
        total: Maximum HP value
        
    Returns:
        str: Health bar string like "🟥🟥🟥⬛⬛⬛⬛⬛⬛⬛"
    """
    ratio = max(0, min(current / total, 1))
    filled = int(ratio * 10)
    return "🟥" * filled + "⬛" * (10 - filled)


# ==========================================
# MAIN COMBAT EMBED
# ==========================================

def combat_embed(
    enemy_name: str,
    color: int,
    player_hp: int,
    player_max_hp: int,
    enemy_hp: int,
    enemy_max_hp: int,
    combat_log: str,
    turn: int,
    ki: int,
    tech_effect_text: str
) -> discord.Embed:
    """
    Build the main combat battle embed.
    
    Shows HP bars for both combatants, the combat log,
    and current turn/ki/technique info.
    
    Args:
        enemy_name: Name of the enemy being fought
        color: Embed color (based on enemy type)
        player_hp: Player's current HP
        player_max_hp: Player's maximum HP
        enemy_hp: Enemy's current HP
        enemy_max_hp: Enemy's maximum HP
        combat_log: Text description of the last action
        turn: Current turn number
        ki: Player's current Ki
        tech_effect_text: Description of active technique's effect
        
    Returns:
        discord.Embed: Formatted combat embed
    """
    embed = discord.Embed(
        title=f"⚔️ Duel vs {enemy_name}",
        color=color
    )
    
    # Player HP bar
    player_bar = generate_health_bar(player_hp, player_max_hp)
    embed.add_field(
        name=f"👤 You (HP: {int(player_hp)})",
        value=f"`{player_bar}`",
        inline=False
    )
    
    # Enemy HP bar
    enemy_bar = generate_health_bar(enemy_hp, enemy_max_hp)
    embed.add_field(
        name=f"👹 {enemy_name} (HP: {int(enemy_hp)})",
        value=f"`{enemy_bar}`",
        inline=False
    )
    
    # Combat log (wrapped in monospace block)
    embed.add_field(
        name="📜 Combat Log",
        value=f"```ml\n{combat_log}\n```",
        inline=False
    )
    
    # Footer with turn, Ki, and technique info
    embed.set_footer(
        text=f"Turn: {turn} | Ki: {ki} | Technique: {tech_effect_text}"
    )
    
    return embed


# ==========================================
# VICTORY EMBED
# ==========================================

def victory_embed(
    enemy_name: str,
    final_reward: int,
    combat_mastery_gain: float,
    drop_item: str = None,
    fastest_turn_record: bool = False
) -> discord.Embed:
    """
    Build the victory screen embed when player defeats an enemy.
    
    Args:
        enemy_name: Name of the defeated enemy
        final_reward: Taels earned from the battle
        combat_mastery_gain: Combat Mastery points gained (usually 2.0)
        drop_item: Name of item dropped (if any)
        fastest_turn_record: Whether this was a record-fast kill
        
    Returns:
        discord.Embed: Formatted victory embed
    """
    description = f"The **{enemy_name}** falls!\n"
    description += f"💰 Earned: **{final_reward} Taels**\n"
    description += f"⚔️ Gained: **{combat_mastery_gain} Combat Mastery**"
    
    if drop_item:
        description += f"\n🎁 Dropped: **{drop_item}**"
    
    if fastest_turn_record:
        description += f"\n⚡ **NEW RECORD!** Fastest kill!"
    
    embed = discord.Embed(
        title="🏆 VICTORY",
        description=description,
        color=format_embed_color("win")  # Green
    )
    
    return embed


# ==========================================
# DEFEAT EMBED
# ==========================================

def defeat_embed(
    enemy_name: str,
    tael_loss: int,
    meridian_damage_minutes: int = 10
) -> discord.Embed:
    """
    Build the defeat screen embed when player loses to an enemy.
    
    Args:
        enemy_name: Name of the enemy that defeated the player
        tael_loss: Amount of Taels lost (10% of total)
        meridian_damage_minutes: How long meridians are damaged (default 10)
        
    Returns:
        discord.Embed: Formatted defeat embed
    """
    embed = discord.Embed(
        title="💀 DEFEATED",
        description=(
            f"You fell to **{enemy_name}**.\n"
            f"❌ Lost **{tael_loss}** Taels.\n"
            f"Meridians damaged for {meridian_damage_minutes} minutes."
        ),
        color=format_embed_color("lose")  # Black/dark
    )
    
    return embed


# ==========================================
# FLEE EMBED (Run Away)
# ==========================================

def flee_embed(
    tael_loss: int,
    cooldown_minutes: int = 2
) -> discord.Embed:
    """
    Build the flee screen embed when player runs from battle.
    
    Args:
        tael_loss: Amount of Taels lost (10% of total)
        cooldown_minutes: How long before player can hunt again (default 2)
        
    Returns:
        discord.Embed: Formatted flee embed
    """
    embed = discord.Embed(
        title="🏃♂️ You fled the battle",
        description=(
            f"You escaped but lost **{tael_loss} Taels**.\n"
            f"You cannot hunt for {cooldown_minutes} minutes."
        ),
        color=format_embed_color("lose")
    )
    
    return embed


# ==========================================
# HUNT COOLDOWN EMBED
# ==========================================

def hunt_cooldown_embed(remaining_seconds: int) -> discord.Embed:
    """
    Build the cooldown embed for when a player tries to hunt too soon.
    
    Args:
        remaining_seconds: Seconds remaining on the cooldown
        
    Returns:
        discord.Embed: Formatted cooldown embed
    """
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    
    if minutes > 0:
        time_text = f"{minutes} minute(s) and {seconds} second(s)"
    else:
        time_text = f"{seconds} second(s)"
    
    embed = discord.Embed(
        title="⏳ Escape Recovery",
        description=(
            f"You are still recovering from your last escape.\n"
            f"Please wait **{time_text}** before hunting again."
        ),
        color=format_embed_color("lose")
    )
    
    return embed


# ==========================================
# ENCOUNTER START EMBED
# ==========================================

def encounter_start_embed(
    enemy_name: str,
    rarity: str,
    color: int,
    player_hp: int,
    player_max_hp: int,
    enemy_hp: int
) -> discord.Embed:
    """
    Build the initial encounter embed shown when a hunt begins.
    
    Args:
        enemy_name: Name of the enemy encountered
        rarity: Rarity tier (Common, Elite, Master, Grandmaster, Mythical)
        color: Embed color based on enemy type
        player_hp: Player's current HP
        player_max_hp: Player's maximum HP
        enemy_hp: Enemy's total HP
        
    Returns:
        discord.Embed: Formatted encounter start embed
    """
    embed = discord.Embed(
        title=f"⚔️ Encounter: {enemy_name}",
        description=f"Rarity: **{rarity}**",
        color=color
    )
    
    # Player HP bar
    player_bar = generate_health_bar(player_hp, player_max_hp)
    embed.add_field(
        name=f"👤 You (HP: {player_hp})",
        value=f"`{player_bar}`",
        inline=False
    )
    
    # Enemy HP bar (full health)
    enemy_bar = generate_health_bar(enemy_hp, enemy_hp)
    embed.add_field(
        name=f"👹 {enemy_name} (HP: {enemy_hp})",
        value=f"`{enemy_bar}`",
        inline=False
    )
    
    return embed


# ==========================================
# LEADERBOARD EMBED
# ==========================================

def leaderboard_embed(
    title: str,
    rows: list,
    mode: str,
    requester_name: str
) -> discord.Embed:
    """
    Build the leaderboard embed for hunt statistics.
    
    Args:
        title: Embed title (e.g., "🏆 Most Hunts (Lifetime)")
        rows: List of tuples (rank, user_name, value)
        mode: Leaderboard mode (affects formatting)
        requester_name: Name of user who requested the leaderboard
        
    Returns:
        discord.Embed: Formatted leaderboard embed
    """
    embed = discord.Embed(
        title=title,
        color=format_embed_color("main")
    )
    
    if not rows:
        embed.description = "No data yet. Go hunt!"
    else:
        description = ""
        for rank, user_name, value in rows:
            if mode == "fastest_kill":
                description += f"{rank}. {user_name} – **{value} turns**\n"
            else:
                description += f"{rank}. {user_name} – **{value}**\n"
        embed.description = description
    
    embed.set_footer(text=f"Requested by {requester_name}")
    return embed


# ==========================================
# TECHNIQUE DISABLED EMBED
# ==========================================

def technique_disabled_embed() -> discord.Embed:
    """
    Build the embed shown when a player has no technique equipped.
    
    Returns:
        discord.Embed: Formatted technique disabled embed
    """
    embed = discord.Embed(
        title="❌ No Technique",
        description="You don't have a martial technique equipped!\nUse `!selecttech` to choose one.",
        color=format_embed_color("error")
    )
    return embed


# ==========================================
# NOT ENOUGH KI EMBED
# ==========================================

def not_enough_ki_embed(required_ki: int = 15) -> discord.Embed:
    """
    Build the embed shown when a player doesn't have enough Ki for a technique.
    
    Args:
        required_ki: Amount of Ki required (default 15)
        
    Returns:
        discord.Embed: Formatted insufficient Ki embed
    """
    embed = discord.Embed(
        title="✨ Insufficient Ki",
        description=f"You need **{required_ki} Ki** to use your technique.",
        color=format_embed_color("error")
    )
    return embed


# ==========================================
# MERIDIAN DAMAGE EMBED
# ==========================================

def meridian_damage_embed() -> discord.Embed:
    """
    Build the embed shown when a player tries to hunt with meridian damage.
    
    Returns:
        discord.Embed: Formatted meridian damage embed
    """
    embed = discord.Embed(
        title="💢 Meridians Damaged",
        description="Your meridians are damaged. You cannot hunt right now.\nUse `!recover` or wait for them to heal.",
        color=format_embed_color("error")
    )
    return embed


# ==========================================
# MORTAL CANNOT HUNT EMBED
# ==========================================

def mortal_cannot_hunt_embed() -> discord.Embed:
    """
    Build the embed shown when a mortal (unranked) player tries to hunt.
    
    Returns:
        discord.Embed: Formatted mortal restriction embed
    """
    embed = discord.Embed(
        title="❌ Cannot Hunt",
        description="Mortals cannot hunt spirit beasts.\nCultivate to reach **Third-Rate Warrior** first!",
        color=format_embed_color("error")
    )
    return embed


# ==========================================
# ALREADY IN COMBAT EMBED
# ==========================================

def already_in_combat_embed() -> discord.Embed:
    """
    Build the embed shown when a player tries to start a new hunt while already in combat.
    
    Returns:
        discord.Embed: Formatted already in combat embed
    """
    embed = discord.Embed(
        title="⚔️ Already in Combat",
        description="You are already fighting! Finish your current battle first.",
        color=format_embed_color("error")
    )
    return embed


print("[DEBUG] combat_embeds.py: Combat embeds loaded successfully")