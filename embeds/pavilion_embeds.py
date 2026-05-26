"""
embeds/pavilion_embeds.py - Embed designs for Pavilion cog
Contains all embed builders for technique selection, viewing, and management.

This file handles:
- Pavilion main menu embed
- Technique inspection embed (detailed view)
- Technique list embed (all available techniques)
- Reset confirmation embed
- Reset success embed
- Current technique embed (when already has a technique)
- Error embeds (insufficient Ki, rank requirement, etc.)
"""

import discord
from backend.helpers import format_embed_color
from typing import Dict, Any, Optional, List

print("[DEBUG] pavilion_embeds.py: Loading pavilion embeds...")


# ==========================================
# FAMILY COLORS AND EMOJIS
# ==========================================

FAMILY_DATA = {
    "Orthodox": {
        "emoji": "⚜️",
        "color": 0x43B581,  # Green
        "name": "Orthodox"
    },
    "Unorthodox": {
        "emoji": "🌙",
        "color": 0x9B59B6,  # Purple
        "name": "Unorthodox"
    },
    "Demonic": {
        "emoji": "🩸",
        "color": 0xE74C3C,  # Red
        "name": "Demonic"
    }
}

TECHNIQUE_TYPE_EMOJIS = {
    "Movement": "💨",
    "Strike": "👊",
    "Defense": "🛡️",
    "Recovery": "💚",
    "Healing": "❤️"
}


def get_family_data(family: str) -> Dict[str, Any]:
    """
    Get data for a technique family.
    
    Args:
        family: Family name (Orthodox, Unorthodox, Demonic)
        
    Returns:
        Dict with emoji, color, and name
    """
    return FAMILY_DATA.get(family, FAMILY_DATA["Unorthodox"])


def get_technique_type_emoji(tech_type: str) -> str:
    """
    Get emoji for a technique type.
    
    Args:
        tech_type: Type of technique (Movement, Strike, Defense, Recovery, Healing)
        
    Returns:
        Emoji string for the type
    """
    return TECHNIQUE_TYPE_EMOJIS.get(tech_type, "📜")


# ==========================================
# PAVILION MAIN MENU EMBED
# ==========================================

def pavilion_main_embed(
    user_rank: str,
    current_ki: int,
    ki_required: int,
    has_active_tech: bool = False,
    active_tech_name: str = None,
    active_tech_mastery: float = None
) -> discord.Embed:
    """
    Build the main Pavilion menu embed.
    
    Args:
        user_rank: User's current cultivation rank
        current_ki: User's current Ki
        ki_required: Ki required to access Pavilion (100)
        has_active_tech: Whether user already has a technique
        active_tech_name: Name of active technique (if any)
        active_tech_mastery: Mastery percentage of active technique (if any)
        
    Returns:
        discord.Embed: Formatted pavilion main menu
    """
    embed = discord.Embed(
        title="🏮 Pavilion of Hidden Scrolls",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "The sacred texts whisper your name...\n\n"
            f"📊 **Your Cultivation:** {user_rank}\n"
            f"✨ **Ki:** {current_ki}/{ki_required} (required to read scrolls)"
        ),
        color=format_embed_color("main")
    )
    
    if has_active_tech and active_tech_name:
        embed.add_field(
            name="📜 Your Current Focus",
            value=f"**{active_tech_name}**\nMastery: `{active_tech_mastery:.1f}%` / 100%",
            inline=False
        )
        embed.set_footer(text="Use !reset_technique to abandon your current path (costs 500 Taels)")
    else:
        embed.description += "\n\nSelect a scroll from the menu below to begin your training."
        embed.set_footer(text="The Pavilion awaits your choice...")
    
    return embed


# ==========================================
# TECHNIQUE INSPECTION EMBED
# ==========================================

def technique_inspect_embed(
    tech_name: str,
    tech_data: Dict[str, Any],
    user_rank: str,
    meets_requirements: bool = True
) -> discord.Embed:
    """
    Build the technique inspection embed when a user selects a scroll.
    
    Args:
        tech_name: Name of the technique
        tech_data: Technique data from constants
        user_rank: User's current rank
        meets_requirements: Whether user meets rank requirement
        
    Returns:
        discord.Embed: Formatted technique inspection embed
    """
    family = tech_data.get("family", "Unorthodox")
    family_data = get_family_data(family)
    tech_type = tech_data.get("type", "Unknown")
    type_emoji = get_technique_type_emoji(tech_type)
    rank_required = tech_data.get("rank_required", "None")
    effect_text = tech_data.get("effect_text", "Unknown effect.")
    story = tech_data.get("story", "The scroll is ancient and mysterious.")
    
    embed = discord.Embed(
        title=f"📜 {tech_name}",
        description=(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{type_emoji} **Type:** {tech_type}\n"
            f"{family_data['emoji']} **Family:** {family}\n"
            f"⭐ **Requirement:** {rank_required}\n\n"
            f"*{story}*\n\n"
            f"🔹 **Effect:** {effect_text}"
        ),
        color=family_data["color"] if meets_requirements else format_embed_color("error")
    )
    
    if not meets_requirements:
        embed.add_field(
            name="❌ Path Blocked",
            value=f"Your cultivation ({user_rank}) is not yet sufficient.\nYou need to reach **{rank_required}** to learn this technique.",
            inline=False
        )
        embed.set_footer(text="Continue your cultivation and return when you are stronger.")
    else:
        embed.set_footer(text="If this path calls to you, click 'Begin Training' below.")
    
    return embed


# ==========================================
# TECHNIQUE LIST EMBED (!techniques)
# ==========================================

def techniques_list_embed(techniques: List[tuple]) -> discord.Embed:
    """
    Build the embed listing all available techniques.
    
    Args:
        techniques: List of tuples (tech_name, tech_data)
        
    Returns:
        discord.Embed: Formatted techniques list embed
    """
    embed = discord.Embed(
        title="📚 Martial Techniques",
        description="━━━━━━━━━━━━━━━━━━━━━━━━━\nThese are the techniques you can learn at the Pavilion.",
        color=format_embed_color("teal")
    )
    
    # Group by family for better organization
    orthodox_techs = []
    unorthodox_techs = []
    demonic_techs = []
    
    for tech_name, tech_data in techniques:
        family = tech_data.get("family", "Unorthodox")
        type_emoji = get_technique_type_emoji(tech_data.get("type", "Unknown"))
        effect = tech_data.get("effect_text", "Unknown effect")[:60]
        rank_req = tech_data.get("rank_required", "None")
        
        line = f"{type_emoji} **{tech_name}**\n└─ *{effect}* (Req: {rank_req})"
        
        if family == "Orthodox":
            orthodox_techs.append(line)
        elif family == "Demonic":
            demonic_techs.append(line)
        else:
            unorthodox_techs.append(line)
    
    # Add fields (2 columns if possible, but Discord limits)
    if orthodox_techs:
        embed.add_field(
            name="⚜️ Orthodox Techniques",
            value="\n".join(orthodox_techs) if orthodox_techs else "None",
            inline=False
        )
    
    if unorthodox_techs:
        embed.add_field(
            name="🌙 Unorthodox Techniques",
            value="\n".join(unorthodox_techs) if unorthodox_techs else "None",
            inline=False
        )
    
    if demonic_techs:
        embed.add_field(
            name="🩸 Demonic Techniques",
            value="\n".join(demonic_techs) if demonic_techs else "None",
            inline=False
        )
    
    embed.set_footer(text="Visit !pavilion to choose a technique")
    
    return embed


# ==========================================
# CURRENT TECHNIQUE EMBED
# ==========================================

def current_technique_embed(
    tech_name: str,
    mastery: float,
    reset_cost: int = 500
) -> discord.Embed:
    """
    Build the embed shown when user already has a technique.
    
    Args:
        tech_name: Name of current technique
        mastery: Current mastery percentage
        reset_cost: Cost to reset technique (default 500)
        
    Returns:
        discord.Embed: Formatted current technique embed
    """
    embed = discord.Embed(
        title="🏮 Pavilion: Current Focus",
        description=(
            f"You are currently focusing on **{tech_name}**.\n"
            f"📊 **Mastery:** `{mastery:.1f}%` / 100%\n\n"
            f"To switch techniques, use `!reset_technique` (costs {reset_cost} Taels)."
        ),
        color=format_embed_color("main")
    )
    return embed


# ==========================================
# RESET CONFIRMATION EMBED
# ==========================================

def reset_confirmation_embed(
    tech_name: str,
    mastery: float,
    reset_cost: int
) -> discord.Embed:
    """
    Build the reset confirmation embed.
    
    Args:
        tech_name: Name of technique being abandoned
        mastery: Current mastery percentage being lost
        reset_cost: Taels cost to reset
        
    Returns:
        discord.Embed: Formatted confirmation embed
    """
    embed = discord.Embed(
        title="⚠️ Confirm Technique Reset",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Are you sure you want to abandon **{tech_name}**?\n\n"
            f"📊 **Mastery Lost:** `{mastery:.1f}%`\n"
            f"💰 **Cost:** {reset_cost} Taels\n\n"
            "⚠️ This action cannot be undone."
        ),
        color=format_embed_color("lose")
    )
    return embed


def reset_success_embed(
    old_tech: str,
    lost_mastery: float,
    cost: int,
    new_taels: int
) -> discord.Embed:
    """
    Build the reset success embed.
    
    Args:
        old_tech: Name of abandoned technique
        lost_mastery: Mastery percentage lost
        cost: Taels cost deducted
        new_taels: Remaining Taels after deduction
        
    Returns:
        discord.Embed: Formatted success embed
    """
    embed = discord.Embed(
        title="🔄 Technique Reset",
        description=(
            f"You have abandoned **{old_tech}**.\n"
            f"📊 Lost `{lost_mastery:.1f}%` mastery.\n"
            f"💰 Deducted {cost} Taels.\n\n"
            f"💎 Remaining Taels: {new_taels}\n\n"
            f"You may now choose a new path with `!pavilion`."
        ),
        color=format_embed_color("gold")
    )
    return embed


# ==========================================
# ERROR EMBEDS
# ==========================================

def insufficient_ki_embed(current_ki: int, required_ki: int = 100) -> discord.Embed:
    """
    Build embed for insufficient Ki to enter Pavilion.
    
    Args:
        current_ki: User's current Ki
        required_ki: Ki required (default 100)
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Insufficient Ki",
        description=(
            f"The scrolls are sealed to the uninitiated.\n"
            f"You need **{required_ki} Ki** to understand these foundations.\n"
            f"✨ Current Ki: {current_ki}\n\n"
            f"Use `!observe` or `!comprehend` to refine your Ki."
        ),
        color=format_embed_color("error")
    )
    return embed


def rank_requirement_embed(
    tech_name: str,
    required_rank: str,
    user_rank: str
) -> discord.Embed:
    """
    Build embed for insufficient rank to learn a technique.
    
    Args:
        tech_name: Name of the technique
        required_rank: Rank required
        user_rank: User's current rank
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Path Blocked",
        description=(
            f"The secrets of **{tech_name}** are beyond your current realm.\n\n"
            f"⭐ **Required:** {required_rank}\n"
            f"📊 **Your Rank:** {user_rank}\n\n"
            f"Continue your cultivation and return when you are stronger."
        ),
        color=format_embed_color("error")
    )
    return embed


def reset_not_possible_embed(current_taels: int, reset_cost: int = 500) -> discord.Embed:
    """
    Build embed for insufficient Taels to reset technique.
    
    Args:
        current_taels: User's current Taels
        reset_cost: Cost to reset (default 500)
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Insufficient Taels",
        description=(
            f"You need **{reset_cost} Taels** to reset your technique.\n"
            f"💰 Current Taels: {current_taels}\n\n"
            f"Use `!work` or `!hunt` to earn more."
        ),
        color=format_embed_color("error")
    )
    return embed


def already_meditating_embed() -> discord.Embed:
    """
    Build embed for when user is meditating and can't access Pavilion.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="🧘 Deep in Meditation",
        description=(
            "Your mind is currently focused on inner cultivation.\n"
            "Use `!cancel` to stop meditating before visiting the Pavilion."
        ),
        color=format_embed_color("error")
    )
    return embed


def no_technique_to_reset_embed() -> discord.Embed:
    """
    Build embed for when user tries to reset but has no technique.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ No Technique to Reset",
        description="You are not currently focusing on any technique.\nUse `!pavilion` to choose your first technique.",
        color=format_embed_color("error")
    )
    return embed


def feature_disabled_embed() -> discord.Embed:
    """
    Build embed for when Pavilion feature is disabled.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Pavilion Closed",
        description="The Pavilion of Hidden Scrolls is currently closed by the elders.",
        color=format_embed_color("error")
    )
    return embed


print("[DEBUG] pavilion_embeds.py: Pavilion embeds loaded successfully")