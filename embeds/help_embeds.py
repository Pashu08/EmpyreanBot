"""
embeds/help_embeds.py - Embed designs for Help cog
Contains all embed builders for the interactive help system.

This file handles:
- Main help menu embed (category selector)
- Category embeds (list of commands in a category)
- Command detail embed (for !help <command>)
- Error embeds for help system
"""

import discord
from backend.helpers import format_embed_color
from typing import List, Dict, Optional, Tuple

print("[DEBUG] help_embeds.py: Loading help embeds...")


# ==========================================
# EMOJI MAPPINGS FOR COMMANDS
# ==========================================

# Emojis for different command types (used in category embeds)
COMMAND_EMOJIS = {
    # Genesis & Basics
    "start": "🏁",
    "stats": "📊",
    "profile": "👤",
    "pstatus": "📈",
    "afk": "😴",
    "pouch": "💰",
    
    # Cultivation & Training
    "observe": "👁️",
    "comprehend": "🧠",
    "pavilion": "🏛️",
    "techniques": "📜",
    "reset_technique": "🔄",
    "breakthrough": "🌀",
    "breakthrough_status": "📊",
    
    # Combat & Warfare
    "hunt": "⚔️",
    "spar": "🥋",
    "huntleaderboard": "🏆",
    
    # Inventory & Shop
    "inventory": "🎒",
    "use": "✨",
    "bazaar": "🏪",
    "buy": "🛒",
    "sell": "💸",
    "give": "🎁",
    "search": "🔍",
    
    # Daily Actions & Recovery
    "work": "⚒️",
    "recover": "💚",
    "cancel": "❌",
    "meditate": "🧘",
    "focus": "🎯",
    "rest": "😴",
    "toggle_dm": "📬",
}


def get_command_emoji(command_name: str) -> str:
    """
    Get the emoji for a specific command.
    
    Args:
        command_name: Name of the command
        
    Returns:
        str: Emoji for the command, or default emoji if not found
    """
    return COMMAND_EMOJIS.get(command_name.lower(), "📌")


# ==========================================
# MAIN HELP MENU EMBED
# ==========================================

def main_help_embed() -> discord.Embed:
    """
    Build the main help menu embed.
    
    This embed is shown when a user types !help.
    It displays the welcome message and instructs users to select a category.
    
    Returns:
        discord.Embed: Formatted main help menu embed
    """
    embed = discord.Embed(
        title="📜 The Path of the Bound: Complete Manual",
        description=(
            "Welcome to the world of **Empyrean Ascent**.\n\n"
            "Select a category below to begin your study.\n"
            "💡 **Tip:** Many commands have short aliases (e.g., `!st` for `!stats`).\n\n"
            "📖 **For command details:** Type `!help <command>` (e.g., `!help hunt`)\n\n"
            "⚙️ **Admin commands** are available via `!divine` (admin only)."
        ),
        color=format_embed_color("main")
    )
    
    # Add footer with helpful tip
    embed.set_footer(text="The heavens watch every step you take.")
    
    return embed


# ==========================================
# CATEGORY EMBED (List of commands in a category)
# ==========================================

def category_embed(
    category_name: str,
    category_emoji: str,
    commands_list: List[Tuple[str, str, Optional[List[str]]]],
    category_description: str = ""
) -> discord.Embed:
    """
    Build an embed for a help category showing all commands.
    
    Args:
        category_name: Name of the category (e.g., "Combat & Warfare")
        category_emoji: Emoji for the category (e.g., "⚔️")
        commands_list: List of tuples (command_name, description, aliases)
                       Example: [("hunt", "Hunt spirit beasts", ["h"]), ...]
        category_description: Optional description text for the category
        
    Returns:
        discord.Embed: Formatted category embed
        
    Example:
        >>> embed = category_embed("Combat & Warfare", "⚔️", 
        ...     [("hunt", "Hunt spirit beasts", ["h"])])
    """
    # Build title with emoji
    title = f"{category_emoji} {category_name}"
    
    embed = discord.Embed(
        title=title,
        color=format_embed_color("teal")
    )
    
    # Add category description if provided
    if category_description:
        embed.description = category_description
    
    # Build command list
    command_text = ""
    for cmd_name, description, aliases in commands_list:
        emoji = get_command_emoji(cmd_name)
        
        # Add aliases if they exist
        alias_text = ""
        if aliases and len(aliases) > 0:
            alias_list = ", ".join([f"`!{a}`" for a in aliases if a != cmd_name])
            if alias_list:
                alias_text = f"\n└─ *Aliases: {alias_list}*"
        
        # Format: "🔹 **!command** - Description"
        command_text += f"{emoji} **!{cmd_name}** - {description}{alias_text}\n"
    
    # Split if too long (Discord embed field limit is 1024 chars)
    if len(command_text) > 900:
        # Split into multiple fields
        lines = command_text.split("\n")
        current_field = ""
        field_count = 1
        
        for line in lines:
            if len(current_field) + len(line) + 1 > 900:
                embed.add_field(
                    name=f"📜 Commands (Part {field_count})",
                    value=current_field,
                    inline=False
                )
                current_field = line + "\n"
                field_count += 1
            else:
                current_field += line + "\n"
        
        if current_field:
            embed.add_field(
                name=f"📜 Commands (Part {field_count})",
                value=current_field,
                inline=False
            )
    else:
        embed.add_field(name="📜 Commands", value=command_text, inline=False)
    
    # Footer with navigation tip
    embed.set_footer(text="Use !help <command> for detailed info • Select another category from the menu")
    
    return embed


# ==========================================
# COMMAND DETAIL EMBED (for !help <command>)
# ==========================================

def command_detail_embed(
    command_name: str,
    description: str,
    aliases: List[str],
    usage_example: str,
    cooldown: Optional[int] = None,
    long_description: Optional[str] = None
) -> discord.Embed:
    """
    Build a detailed embed for a specific command.
    
    This is shown when a user types `!help hunt` or similar.
    
    Args:
        command_name: Name of the command (e.g., "hunt")
        description: Short description of what the command does
        aliases: List of alias names (e.g., ["h"])
        usage_example: Example usage (e.g., "!hunt")
        cooldown: Cooldown in seconds (if any)
        long_description: Optional detailed explanation
        
    Returns:
        discord.Embed: Formatted command detail embed
        
    Example:
        >>> embed = command_detail_embed(
        ...     "hunt", "Hunt spirit beasts", ["h"], "!hunt", cooldown=600
        ... )
    """
    emoji = get_command_emoji(command_name)
    
    embed = discord.Embed(
        title=f"{emoji} Command: !{command_name}",
        color=format_embed_color("gold")
    )
    
    # Short description
    embed.add_field(name="📝 Description", value=description, inline=False)
    
    # Long description (if provided)
    if long_description:
        embed.add_field(name="📖 Details", value=long_description, inline=False)
    
    # Aliases
    if aliases and len(aliases) > 0:
        alias_list = ", ".join([f"`!{a}`" for a in aliases if a != command_name])
        if alias_list:
            embed.add_field(name="🔗 Aliases", value=alias_list, inline=True)
    
    # Usage example
    embed.add_field(name="💡 Usage", value=f"`{usage_example}`", inline=True)
    
    # Cooldown (if applicable)
    if cooldown and cooldown > 0:
        if cooldown >= 60:
            minutes = cooldown // 60
            seconds = cooldown % 60
            cooldown_text = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes} minutes"
        else:
            cooldown_text = f"{cooldown} seconds"
        embed.add_field(name="⏳ Cooldown", value=cooldown_text, inline=True)
    
    # Footer
    embed.set_footer(text="Use the dropdown menu to explore other commands")
    
    return embed


# ==========================================
# ERROR EMBEDS
# ==========================================

def command_not_found_embed(command_name: str) -> discord.Embed:
    """
    Build an error embed for when a command is not found.
    
    Args:
        command_name: The command the user tried to look up
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Command Not Found",
        description=f"The command `!{command_name}` does not exist.\n\nUse `!help` to see all available commands.",
        color=format_embed_color("error")
    )
    
    return embed


def help_disabled_embed() -> discord.Embed:
    """
    Build an error embed for when the help feature is disabled.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Help Disabled",
        description="The help system is currently disabled by an administrator.",
        color=format_embed_color("error")
    )
    
    return embed


def no_command_specified_embed() -> discord.Embed:
    """
    Build an embed for when user types `!help` with no arguments.
    This is informational, not an error - shows how to use help.
    
    Returns:
        discord.Embed: Formatted informational embed
    """
    embed = discord.Embed(
        title="📚 Help System",
        description=(
            "To view the full help menu with categories, type `!help` by itself.\n\n"
            "To get detailed info about a specific command, type `!help <command>`\n"
            "**Example:** `!help hunt`\n\n"
            "**Quick tips:**\n"
            "• `!stats` - View your cultivation progress\n"
            "• `!work` - Earn Taels\n"
            "• `!hunt` - Fight spirit beasts"
        ),
        color=format_embed_color("teal")
    )
    
    return embed


# ==========================================
# WELCOME / TUTORIAL EMBED (Optional)
# ==========================================

def welcome_help_embed() -> discord.Embed:
    """
    Build a welcome embed for first-time users.
    Can be sent when a user joins or uses !help for the first time.
    
    Returns:
        discord.Embed: Formatted welcome embed
    """
    embed = discord.Embed(
        title="🏮 Welcome to Empyrean Ascent",
        description=(
            "Embark on a journey of cultivation, combat, and mastery.\n\n"
            "**Quick Start Guide:**\n"
            "1. `!start` - Create your character\n"
            "2. `!pavilion` - Choose a martial technique\n"
            "3. `!work` - Earn your first Taels\n"
            "4. `!hunt` - Test your strength\n\n"
            "For a complete list of commands, type `!help`"
        ),
        color=format_embed_color("win")
    )
    
    embed.set_footer(text="The path to immortality begins with a single step")
    
    return embed


print("[DEBUG] help_embeds.py: Help embeds loaded successfully")