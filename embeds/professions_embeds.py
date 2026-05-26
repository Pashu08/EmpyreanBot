"""
embeds/professions_embeds.py - Embed designs for Professions cog
Contains all embed builders for profession selection and status viewing.

This file handles:
- Profession list embed (when user types !pchoose with no argument)
- Profession chosen confirmation embed
- Profession status embed (current progress and rank)
- Error embeds (already has profession, no profession)
"""

import discord
from backend.helpers import format_embed_color

print("[DEBUG] professions_embeds.py: Loading professions embeds...")


# ==========================================
# PROFESSION LIST EMBED
# ==========================================

def profession_list_embed(professions_list: list) -> discord.Embed:
    """
    Build the embed showing all available professions.
    
    Args:
        professions_list: List of profession names (e.g., ["Alchemist", "Blacksmith", ...])
        
    Returns:
        discord.Embed: Formatted profession list embed
    """
    # Format the list with bullet points
    list_str = "\n".join([f"• {p}" for p in professions_list])
    
    embed = discord.Embed(
        title="⚒️ Choose Your Profession",
        description=f"Use `!pchoose <name>` to select your path:\n\n{list_str}",
        color=format_embed_color("main")  # Dark red/burgundy
    )
    
    return embed


# ==========================================
# PROFESSION CHOSEN CONFIRMATION EMBED
# ==========================================

def profession_chosen_embed(profession_name: str) -> discord.Embed:
    """
    Build the confirmation embed after a user chooses a profession.
    
    Args:
        profession_name: Name of the chosen profession
        
    Returns:
        discord.Embed: Formatted success embed
    """
    embed = discord.Embed(
        title="✅ Profession Bound",
        description=f"You have begun your journey as a **{profession_name}**.\nThis choice is permanent.",
        color=format_embed_color("win")  # Green for success
    )
    
    return embed


# ==========================================
# PROFESSION STATUS EMBED
# ==========================================

def profession_status_embed(
    profession_name: str,
    rank: str,
    current_xp: int,
    required_xp: int,
    progress_bar: str,
    percent: int
) -> discord.Embed:
    """
    Build the embed showing a user's profession progress.
    
    Args:
        profession_name: Name of the profession
        rank: Current rank (e.g., "Apprentice")
        current_xp: Current experience points
        required_xp: XP needed for next rank
        progress_bar: Visual progress bar string
        percent: Percentage completion
        
    Returns:
        discord.Embed: Formatted profession status embed
    """
    embed = discord.Embed(
        title="📜 Professional Standing",
        color=format_embed_color("main")
    )
    
    embed.add_field(name="Path", value=profession_name, inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(
        name="Experience",
        value=f"{progress_bar} **{percent}%**\n{current_xp} / {required_xp} XP",
        inline=False
    )
    embed.add_field(
        name="⭐ Talent",
        value="**Professional Insight**\n✨ +10% XP Gain\n✨ +5% Success Rate",
        inline=False
    )
    
    return embed


# ==========================================
# ERROR EMBEDS
# ==========================================

def already_has_profession_embed(profession_name: str) -> discord.Embed:
    """
    Build the error embed shown when a user already has a profession.
    
    Args:
        profession_name: Name of the user's current profession
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="📜 Path Already Chosen",
        description=f"You are already dedicated to the path of a **{profession_name}**.",
        color=format_embed_color("error")
    )
    
    return embed


def no_profession_embed() -> discord.Embed:
    """
    Build the error embed shown when a user tries to check status
    but hasn't chosen a profession yet.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="📜 Profession Required",
        description="You must choose a profession before viewing progress.\nUse `!pchoose` to select your path.",
        color=format_embed_color("error")
    )
    
    return embed


def not_registered_embed() -> discord.Embed:
    """
    Build the error embed shown when a user isn't registered.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Not Registered",
        description="You haven't begun your journey yet. Use `!start` to create your character.",
        color=format_embed_color("error")
    )
    
    return embed


def profession_not_found_embed(invalid_profession: str, professions_list: list) -> discord.Embed:
    """
    Build the error embed shown when a user tries to choose an invalid profession.
    
    Args:
        invalid_profession: The invalid profession name the user typed
        professions_list: List of valid profession names
        
    Returns:
        discord.Embed: Formatted error embed with valid options
    """
    list_str = ", ".join(professions_list)
    
    embed = discord.Embed(
        title="❌ Invalid Profession",
        description=f"`{invalid_profession}` is not a valid path.\n\nValid professions: {list_str}",
        color=format_embed_color("error")
    )
    
    return embed


def feature_disabled_embed() -> discord.Embed:
    """
    Build the embed shown when professions feature is disabled.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Feature Disabled",
        description="The professions system is currently disabled by an administrator.",
        color=format_embed_color("error")
    )
    
    return embed


print("[DEBUG] professions_embeds.py: Professions embeds loaded successfully")