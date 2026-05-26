"""
embeds/core_embeds.py - Embed designs for Core cog
Contains all embed builders for character creation and tutorials.

This file handles:
- Start menu embed (background selection screen)
- Character creation success embed
- Tutorial embed sent to new players
"""

import discord
from backend.helpers import format_embed_color

print("[DEBUG] core_embeds.py: Loading core embeds...")


# ==========================================
# START MENU EMBED (Background Selection)
# ==========================================

def start_menu_embed() -> discord.Embed:
    """
    Build the embed for the !start command background selection menu.
    
    This embed displays the three available backgrounds (Laborer, Outcast, Hermit)
    with their descriptions and perks, allowing the user to choose their origin.
    
    Returns:
        discord.Embed: Formatted start menu embed with background options
    """
    embed = discord.Embed(
        title="🏮 Murim: Empyrean Ascent 🏮",
        description=(
            "Welcome, seeker. The path to immortality is paved with blood, ki, and resolve. "
            "Before you take your first step, you must choose your origin.\n\n"
            
            "**⚒️ Laborer**\n"
            "*Used to hardship. Gains Taels easily and has a knack for technique mastery.*\n\n"
            
            "**🌑 Outcast**\n"
            "*Shunned by society. Gains access to the Underworld Bazaar and forbidden goods.*\n\n"
            
            "**🌿 Hermit**\n"
            "*A soul of nature. Regenerates Vitality and HP faster than any other.*\n\n"
            
            "**Select your background below to begin.**"
        ),
        color=format_embed_color("main")  # Dark red/burgundy theme color
    )
    
    embed.set_footer(text="Your choice is permanent. Choose with wisdom.")
    
    return embed


# ==========================================
# CHARACTER CREATION SUCCESS EMBED
# ==========================================

def character_success_embed(background_name: str, item_name: str) -> discord.Embed:
    """
    Build the success embed shown after a player creates their character.
    
    Args:
        background_name: The background chosen (Laborer, Outcast, or Hermit)
        item_name: The starting item granted (Torn Page, Black Coin, or Glowing Fruit)
        
    Returns:
        discord.Embed: Formatted success embed with character details
        
    Example:
        >>> embed = character_success_embed("Laborer", "Torn Page")
    """
    embed = discord.Embed(
        title="🌅 A New Legend Begins",
        description=(
            f"The heavens tremble as you step forward. You have chosen the path of the **{background_name}**.\n\n"
            f"**Initial Item:** `{item_name}`\n"
            f"**Current Status:** The Bound (Mortal)\n\n"
            "*Go forth and cultivate. Your ascent begins now.*"
        ),
        color=format_embed_color("win")  # Green for success
    )
    
    return embed


# ==========================================
# TUTORIAL EMBED (Sent to new players)
# ==========================================

def tutorial_embed() -> discord.Embed:
    """
    Build the tutorial embed sent to new players after character creation.
    
    This embed contains essential commands to help new players get started:
    - Resource earning (work, observe)
    - Growth commands (comprehend, stats)
    - Exploration (pavilion, bazaar)
    - Combat (hunt, spar)
    
    Returns:
        discord.Embed: Formatted tutorial embed with command list
    """
    embed = discord.Embed(
        title="📜 Your Journey Begins",
        description=(
            "Welcome to **Murim: Empyrean Ascent**!\n\n"
            "Here are a few commands to get you started:\n\n"
            
            "**💰 Earn Resources**\n"
            "• `!work` – Perform labor to earn Taels (costs Vitality)\n"
            "• `!observe` – Meditate to refine Ki and gain Mastery\n\n"
            
            "**📈 Grow Stronger**\n"
            "• `!comprehend` – Deeply study your technique for major Mastery gains\n"
            "• `!stats` – View your cultivation progress\n\n"
            
            "**🛒 Explore**\n"
            "• `!pavilion` – Choose a martial technique to learn\n"
            "• `!bazaar` – Buy items to aid your journey\n\n"
            
            "**⚔️ Fight**\n"
            "• `!hunt` – Hunt spirit beasts for rewards\n"
            "• `!spar @user` – Challenge another player to a friendly duel\n\n"
            
            "For a full list of commands, type `!help`.\n\n"
            "*The path to the peak is long. Take your first step.*"
        ),
        color=format_embed_color("teal")  # Teal blue for informational content
    )
    
    return embed


# ==========================================
# ALREADY REGISTERED EMBED
# ==========================================

def already_registered_embed() -> discord.Embed:
    """
    Build the error embed shown when a user who already has a character
    tries to use the !start command again.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Already Registered",
        description="You have already begun your journey. A warrior walks only one path.",
        color=format_embed_color("error")  # Red for error
    )
    
    return embed


# ==========================================
# FEATURE DISABLED EMBED
# ==========================================

def feature_disabled_embed(feature_name: str = "Character Creation") -> discord.Embed:
    """
    Build the embed shown when the core feature is disabled by an admin.
    
    Args:
        feature_name: Name of the disabled feature (default "Character Creation")
        
    Returns:
        discord.Embed: Formatted feature disabled embed
    """
    embed = discord.Embed(
        title="❌ Feature Disabled",
        description=f"The **{feature_name}** feature is currently disabled by an administrator.",
        color=format_embed_color("error")
    )
    
    return embed


# ==========================================
# BANNED USER EMBED
# ==========================================

def banned_user_embed() -> discord.Embed:
    """
    Build the embed shown when a banned user tries to create a character.
    
    Returns:
        discord.Embed: Formatted banned user embed
    """
    embed = discord.Embed(
        title="🔨 Banned",
        description="You are banned from using this bot. Appeal to the administrators.",
        color=format_embed_color("error")
    )
    
    return embed


# ==========================================
# PERMANENT CHOICE WARNING EMBED
# ==========================================

def permanent_choice_warning_embed() -> discord.Embed:
    """
    Build the warning embed reminding users that background choice is permanent.
    This can be used as a follow-up or confirmation message.
    
    Returns:
        discord.Embed: Formatted warning embed
    """
    embed = discord.Embed(
        title="⚠️ Permanent Choice",
        description="Your background choice is **permanent** and cannot be changed later. Choose wisely.",
        color=format_embed_color("gold")  # Gold for warning/info
    )
    
    return embed


print("[DEBUG] core_embeds.py: Core embeds loaded successfully")