"""
embeds/profile_embeds.py - Embed designs for Profile cog
Contains all embed builders for displaying character profiles.

This file handles:
- Main profile embed (detailed character sheet)
- Error embeds (not registered, feature disabled, user not found)
"""

import discord
from backend.helpers import format_embed_color
from typing import Optional

print("[DEBUG] profile_embeds.py: Loading profile embeds...")


# ==========================================
# PROFILE EMBED
# ==========================================

def profile_embed(
    target: discord.Member,
    background: str,
    background_emoji: str,
    background_perk: str,
    background_item: str,
    taels: int,
    profession: str,
    profession_rank: str,
    active_tech: str,
    mastery_percent: Optional[float],
    milestones_reached: int,
    milestones_total: int,
    work_available: bool,
    observe_available: bool,
    reset_hours: int,
    reset_minutes: int,
    hidden_tech_hint: str,
    total_items: int,
    unique_items: int
) -> discord.Embed:
    """
    Build a beautiful, organized profile embed for a player.
    
    Args:
        target: The discord user being displayed
        background: Background name (Laborer, Outcast, Hermit)
        background_emoji: Emoji for the background
        background_perk: Perk description
        background_item: Starting item name
        taels: Player's Taels
        profession: Profession name (or "None")
        profession_rank: Current rank (Apprentice, etc.)
        active_tech: Active technique name (or "None")
        mastery_percent: Mastery percentage (0-100), or None if no technique
        milestones_reached: Number of milestones reached (0-4)
        milestones_total: Total milestones possible (4)
        work_available: Whether work daily bonus is available
        observe_available: Whether observe daily bonus is available
        reset_hours: Hours until daily reset
        reset_minutes: Minutes until daily reset
        hidden_tech_hint: Hint about hidden technique progress
        total_items: Total quantity of items in inventory
        unique_items: Number of unique item types
        
    Returns:
        discord.Embed: Formatted profile embed
    """
    
    embed = discord.Embed(
        title=f"📜 Profile: {target.display_name}",
        color=format_embed_color("teal")
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    # ========== SECTION 1: BASIC INFO ==========
    
    # Background line with emoji
    background_line = f"{background_emoji} **Background:** {background}"
    
    # Perk as sub-line
    perk_line = f"   └─ *{background_perk}*"
    
    # Starting item
    item_line = f"📦 **Starting Item:** {background_item}"
    
    # Profession (with rank if not None)
    if profession and profession != "None":
        profession_line = f"🔮 **Profession:** {profession} ({profession_rank})"
    else:
        profession_line = "🔮 **Profession:** None"
    
    # Wealth with nice formatting
    wealth_line = f"💰 **Wealth:** {taels:,} Taels"
    
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━",
        value=f"{background_line}\n{perk_line}\n\n{item_line}\n\n{profession_line}\n\n{wealth_line}",
        inline=False
    )
    
    # ========== SECTION 2: DAILY BONUSES ==========
    
    work_status = "✅ Available" if work_available else "❌ Used"
    observe_status = "✅ Available" if observe_available else "❌ Used"
    reset_text = f"⏳ Resets in: {reset_hours}h {reset_minutes}m"
    
    daily_value = (
        f"💪 **Work:** {work_status}\n"
        f"👁️ **Observe:** {observe_status}\n"
        f"{reset_text}"
    )
    
    embed.add_field(
        name="🎯 Daily Bonuses",
        value=daily_value,
        inline=False
    )
    
    # ========== SECTION 3: TECHNIQUE MASTERY ==========
    
    if active_tech and active_tech != "None":
        # Mastery progress bar
        if mastery_percent is not None:
            filled = int(mastery_percent / 10)
            bar = "🟩" * filled + "⬛" * (10 - filled)
            mastery_line = f"   └─ Mastery: `{bar}` {mastery_percent:.1f}%"
        else:
            mastery_line = "   └─ Mastery: 0%"
        
        # Milestones
        milestone_percent = int((milestones_reached / milestones_total) * 100) if milestones_total > 0 else 0
        milestone_line = f"   └─ Milestones: {milestones_reached}/{milestones_total} ({milestone_percent}%)"
        
        technique_value = f"📈 **Technique:** {active_tech}\n{mastery_line}\n{milestone_line}\n\n🔒 **Hidden Power:** {hidden_tech_hint}"
    else:
        technique_value = "📈 **Technique:** None selected\n   └─ Visit `!pavilion` to choose a technique"
    
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━",
        value=technique_value,
        inline=False
    )
    
    # ========== SECTION 4: INVENTORY ==========
    
    inventory_value = f"🎒 **Inventory:** {total_items} items ({unique_items} unique)"
    
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━",
        value=inventory_value,
        inline=False
    )
    
    # ========== FOOTER ==========
    
    embed.set_footer(text="💡 Use `!stats` for core cultivation stats (HP, Ki, Rank)")
    
    return embed


# ==========================================
# SIMPLE PROFILE EMBED (for users with no data)
# ==========================================

def simple_profile_embed(target: discord.Member) -> discord.Embed:
    """
    Build a simple profile embed for when user data is incomplete.
    
    Args:
        target: The discord user
        
    Returns:
        discord.Embed: Simple profile embed
    """
    embed = discord.Embed(
        title=f"📜 Profile: {target.display_name}",
        description="This cultivator has not yet begun their journey.",
        color=format_embed_color("teal")
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text="Use `!start` to begin your cultivation journey")
    
    return embed


# ==========================================
# ERROR EMBEDS
# ==========================================

def not_registered_embed(target_name: str = None) -> discord.Embed:
    """
    Build error embed for when a user isn't registered.
    
    Args:
        target_name: Name of the unregistered user (optional)
        
    Returns:
        discord.Embed: Formatted error embed
    """
    if target_name:
        description = f"**{target_name}** has not begun their journey yet."
    else:
        description = "You have not begun your journey yet."
    
    embed = discord.Embed(
        title="❌ Not Registered",
        description=f"{description}\n\nUse `!start` to create your character.",
        color=format_embed_color("error")
    )
    
    return embed


def feature_disabled_embed() -> discord.Embed:
    """
    Build error embed for when profile feature is disabled.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Feature Disabled",
        description="The profile system is currently disabled by an administrator.",
        color=format_embed_color("error")
    )
    
    return embed


def user_not_found_embed() -> discord.Embed:
    """
    Build error embed for when a user can't be found in Discord.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ User Not Found",
        description="Could not find that user. Make sure they are in this server.",
        color=format_embed_color("error")
    )
    
    return embed


def banned_user_embed() -> discord.Embed:
    """
    Build error embed for when a banned user tries to view profile.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="🔨 Banned",
        description="You are banned from using this bot.",
        color=format_embed_color("error")
    )
    
    return embed


print("[DEBUG] profile_embeds.py: Profile embeds loaded successfully")