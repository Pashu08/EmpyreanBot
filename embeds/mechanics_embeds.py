"""
embeds/mechanics_embeds.py - Embed designs for Mechanics cog
Contains all embed builders for meditation, recovery, focus, rest, and heartbeat.

This file handles:
- Meditation progress embed (with animated progress bar)
- Meditation complete embed
- Meditation cancelled embed
- Cooldown embeds for all commands
- Focus, Rest, and Toggle DM embeds
- Heartbeat status embed
- DM notification embeds for heartbeat regen
"""

import discord
from backend.helpers import format_embed_color
from typing import Optional

print("[DEBUG] mechanics_embeds.py: Loading mechanics embeds...")


# ==========================================
# MEDITATION (RECOVER) EMBEDS
# ==========================================

def meditation_start_embed() -> discord.Embed:
    """
    Build the embed shown when a user starts meditating.
    
    Returns:
        discord.Embed: Formatted meditation start embed
    """
    embed = discord.Embed(
        title="🧘 Meditation Begins",
        description="You enter a state of deep meditation… (60 seconds)",
        color=format_embed_color("purple")
    )
    return embed


def meditation_progress_embed(remaining_seconds: int, elapsed_seconds: int, total_seconds: int = 60) -> discord.Embed:
    """
    Build the progress embed for active meditation.
    Updates every 10 seconds to show a visual progress bar.
    
    Args:
        remaining_seconds: Seconds left in meditation
        elapsed_seconds: Seconds elapsed so far
        total_seconds: Total meditation duration (default 60)
        
    Returns:
        discord.Embed: Formatted progress embed with bar
    """
    # Calculate percentage and create progress bar
    percent = max(0, (remaining_seconds / total_seconds) * 100)
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    # Label text based on remaining time
    if remaining_seconds > 0:
        label = f"**{remaining_seconds}s** left…"
    else:
        label = "Almost there…"
    
    embed = discord.Embed(
        title="🧘 Meditating",
        description=f"`[{bar}]` {label}",
        color=format_embed_color("purple")
    )
    return embed


def meditation_complete_embed(
    vit_gain: int,
    ki_gain: int,
    new_vit: int,
    new_ki: int,
    max_vit: int,
    max_ki: int,
    is_hermit: bool = False
) -> discord.Embed:
    """
    Build the embed shown when meditation completes successfully.
    
    Args:
        vit_gain: Vitality gained
        ki_gain: Ki gained
        new_vit: New Vitality total
        new_ki: New Ki total
        max_vit: Maximum Vitality for rank
        max_ki: Maximum Ki for rank
        is_hermit: Whether user has Hermit background (bonus)
        
    Returns:
        discord.Embed: Formatted completion embed
    """
    bonus_text = " *(+Hermit bonus)*" if is_hermit else ""
    
    embed = discord.Embed(
        title="✨ Meditation Complete",
        description=(
            f"You regained **+{vit_gain} Vitality** and **+{ki_gain} Ki**{bonus_text}.\n"
            f"Current: {new_vit}/{max_vit} Vitality | {new_ki}/{max_ki} Ki"
        ),
        color=format_embed_color("win")
    )
    return embed


def meditation_cancelled_embed(penalty_applied: bool = False, penalty_minutes: int = 2) -> discord.Embed:
    """
    Build the embed shown when a user cancels meditation early.
    
    Args:
        penalty_applied: Whether a cooldown penalty was applied
        penalty_minutes: Length of penalty in minutes
        
    Returns:
        discord.Embed: Formatted cancellation embed
    """
    if penalty_applied:
        embed = discord.Embed(
            title="⚠️ Early Cancellation Penalty",
            description=f"Cancelling within 30 seconds applies a {penalty_minutes}-minute cooldown!",
            color=format_embed_color("orange")
        )
    else:
        embed = discord.Embed(
            title="🧘 Meditation Cancelled",
            description="You snap out of your meditation early.",
            color=format_embed_color("orange")
        )
    return embed


def not_meditating_embed() -> discord.Embed:
    """
    Build the embed shown when a user tries to cancel but isn't meditating.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Not Meditating",
        description="You are not currently meditating.",
        color=format_embed_color("error")
    )
    return embed


# ==========================================
# COOLDOWN EMBEDS
# ==========================================

def cooldown_embed(command_name: str, remaining_seconds: int) -> discord.Embed:
    """
    Build a generic cooldown embed for any command.
    
    Args:
        command_name: Name of the command (e.g., "meditate", "focus")
        remaining_seconds: Seconds remaining on cooldown
        
    Returns:
        discord.Embed: Formatted cooldown embed
    """
    # Format time nicely
    if remaining_seconds >= 60:
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        time_text = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes} minutes"
    else:
        time_text = f"{remaining_seconds} seconds"
    
    embed = discord.Embed(
        title="⏳ Cooldown",
        description=f"Please wait **{time_text}** before using `!{command_name}` again.",
        color=format_embed_color("orange")
    )
    return embed


# ==========================================
# FOCUS COMMAND EMBEDS
# ==========================================

def focus_embed(
    new_vit: int,
    new_ki: int,
    max_vit: int,
    max_ki: int,
    vit_cost: int = 10,
    ki_gain: int = 5
) -> discord.Embed:
    """
    Build the embed for the focus command result.
    
    Args:
        new_vit: New Vitality after conversion
        new_ki: New Ki after conversion
        max_vit: Maximum Vitality for rank
        max_ki: Maximum Ki for rank
        vit_cost: Amount of Vitality consumed
        ki_gain: Amount of Ki gained
        
    Returns:
        discord.Embed: Formatted focus result embed
    """
    embed = discord.Embed(
        title="🌀 Focused Energy",
        description=(
            f"You converted **{vit_cost} Vitality** into **{ki_gain} Ki**.\n"
            f"Vitality: {new_vit}/{max_vit}\n"
            f"Ki: {new_ki}/{max_ki}"
        ),
        color=format_embed_color("teal")
    )
    return embed


def low_vitality_embed(required: int, current: int) -> discord.Embed:
    """
    Build the embed shown when a user lacks enough Vitality for focus.
    
    Args:
        required: Vitality required
        current: User's current Vitality
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Low Vitality",
        description=f"You need **{required} Vitality** to focus (you have {current}).",
        color=format_embed_color("error")
    )
    return embed


# ==========================================
# REST COMMAND EMBEDS
# ==========================================

def rest_embed(
    new_hp: int,
    new_vit: int,
    max_hp: int,
    max_vit: int,
    hp_gain: int = 10,
    vit_gain: int = 10
) -> discord.Embed:
    """
    Build the embed for the rest command result.
    
    Args:
        new_hp: New HP after rest
        new_vit: New Vitality after rest
        max_hp: Maximum HP for rank
        max_vit: Maximum Vitality for rank
        hp_gain: Amount of HP gained
        vit_gain: Amount of Vitality gained
        
    Returns:
        discord.Embed: Formatted rest result embed
    """
    embed = discord.Embed(
        title="🛌 Rest Taken",
        description=(
            f"You regain **+{hp_gain} HP** and **+{vit_gain} Vitality**.\n"
            f"HP: {new_hp}/{max_hp} | Vitality: {new_vit}/{max_vit}"
        ),
        color=format_embed_color("win")
    )
    return embed


# ==========================================
# TOGGLE DM EMBED
# ==========================================

def toggle_dm_embed(enabled: bool) -> discord.Embed:
    """
    Build the embed for toggling heartbeat DMs.
    
    Args:
        enabled: True if DMs are now enabled, False if disabled
        
    Returns:
        discord.Embed: Formatted toggle result embed
    """
    status = "enabled" if enabled else "disabled"
    embed = discord.Embed(
        title="✅ DM Toggle",
        description=f"Heartbeat DMs **{status}**.",
        color=format_embed_color("win")
    )
    return embed


# ==========================================
# HEARTBEAT STATUS EMBED (!heartbeat or !hb)
# ==========================================

def heartbeat_status_embed(
    minutes_left: int,
    seconds_left: int,
    regen_amount: int,
    hp: int,
    hp_cap: int,
    vit: int,
    vit_cap: int,
    ki: int,
    ki_cap: int,
    meditate_cd_text: str = ""
) -> discord.Embed:
    """
    Build the embed for !heartbeat command showing next regen and player stats.
    
    Args:
        minutes_left: Minutes until next heartbeat
        seconds_left: Seconds until next heartbeat
        regen_amount: How much HP/Vit will be restored
        hp: Current HP
        hp_cap: Maximum HP
        vit: Current Vitality
        vit_cap: Maximum Vitality
        ki: Current Ki
        ki_cap: Maximum Ki
        meditate_cd_text: Optional cooldown text for meditate command
        
    Returns:
        discord.Embed: Formatted heartbeat status embed
    """
    # Create Ki progress bar
    ki_progress = int((ki / ki_cap) * 100) if ki_cap else 0
    bar_filled = int(ki_progress / 10)
    ki_bar = "█" * bar_filled + "░" * (10 - bar_filled)
    
    embed = discord.Embed(
        title="💓 Heartbeat Status",
        description=f"The heavens will breathe again in **{minutes_left}m {seconds_left}s**.",
        color=format_embed_color("teal")
    )
    
    embed.add_field(
        name="🌿 Next Recovery",
        value=f"Restores **{regen_amount} HP** and **{regen_amount} Vitality**.",
        inline=False
    )
    
    embed.add_field(
        name="📊 Your Progress",
        value=(
            f"🩸 **HP:** {hp}/{hp_cap}\n"
            f"❤️ **Vitality:** {vit}/{vit_cap}\n"
            f"✨ **Ki:** {ki}/{ki_cap} `[{ki_bar}]` {ki_progress}%"
        ),
        inline=False
    )
    
    if meditate_cd_text:
        embed.add_field(name="⏳ Cooldowns", value=meditate_cd_text, inline=False)
    
    embed.set_footer(text="Use `/toggle_dm` to enable/disable heartbeat DMs.")
    
    return embed


def heartbeat_not_ready_embed() -> discord.Embed:
    """
    Build the embed shown when heartbeat timer isn't ready yet.
    
    Returns:
        discord.Embed: Formatted waiting embed
    """
    embed = discord.Embed(
        title="⏳ Heartbeat Not Ready",
        description="Please wait a moment for the heavens to align.",
        color=format_embed_color("orange")
    )
    return embed


# ==========================================
# HEARTBEAT DM EMBED (sent to users)
# ==========================================

def heartbeat_dm_embed(
    hp_gain: int,
    vit_gain: int,
    new_hp: int,
    new_vit: int
) -> discord.Embed:
    """
    Build the DM embed sent to users when heartbeat triggers.
    
    Args:
        hp_gain: Amount of HP regained
        vit_gain: Amount of Vitality regained
        new_hp: New HP total
        new_vit: New Vitality total
        
    Returns:
        discord.Embed: Formatted DM embed
    """
    embed = discord.Embed(
        title="🌿 Heavenly Recovery",
        description=(
            f"You regain **+{hp_gain} HP** and **+{vit_gain} Vitality**.\n"
            f"Current: {new_hp} HP / {new_vit} Vitality"
        ),
        color=format_embed_color("win")
    )
    embed.set_footer(text="You can disable these DMs with /toggle_dm")
    return embed


# ==========================================
# ERROR EMBEDS
# ==========================================

def mechanics_disabled_embed() -> discord.Embed:
    """
    Build the embed shown when mechanics feature is disabled.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Feature Disabled",
        description="The mechanics system is currently disabled by an administrator.",
        color=format_embed_color("error")
    )
    return embed


def not_registered_embed() -> discord.Embed:
    """
    Build the embed shown when a user isn't registered.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Not Registered",
        description="You haven't begun your journey yet. Use `!start` to create your character.",
        color=format_embed_color("error")
    )
    return embed


def already_meditating_embed() -> discord.Embed:
    """
    Build the embed shown when a user tries to meditate while already meditating.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="🧘 Already Meditating",
        description="You are already in a state of deep meditation. Use `!cancel` to stop.",
        color=format_embed_color("error")
    )
    return embed


print("[DEBUG] mechanics_embeds.py: Mechanics embeds loaded successfully")