"""
backend/help_helpers.py - Helper functions and UI views for Help cog

This module handles:
- HelpView class (dropdown menu + button navigation)
- HelpSelect class (category selection dropdown)
- Category data definitions
- Command information retrieval
"""

import discord
from discord.ui import Select, View, Button
from typing import List, Dict, Optional, Tuple
from backend.helpers import format_embed_color
from backend.db import get_bot_setting
from embeds.help_embeds import (
    category_embed,
    command_detail_embed,
    command_not_found_embed,
    help_disabled_embed
)
import config

print("[DEBUG] help_helpers.py: Loading help helpers...")


# ==========================================
# CATEGORY DATA
# ==========================================

# Each category contains:
# - name: Display name
# - emoji: Category emoji
# - description: Optional category description
# - commands: List of (command_name, description, aliases)
#
# Note: Aliases should NOT include the main command name
# Example: "hunt" has alias "h" - so aliases = ["h"]

CATEGORIES = {
    "genesis": {
        "name": "Genesis & Basics",
        "emoji": "🏁",
        "description": "Start your journey and understand your core stats.",
        "commands": [
            ("start", "Begin your journey and choose a background", []),
            ("stats", "View your Rank, Ki, Mastery, and Meridian Health", ["st"]),
            ("profile", "View detailed character sheet", ["prof"]),
            ("pstatus", "View your professional rank and progress", []),
            ("afk", "Check your AFK (away from keyboard) gains", ["away"]),
            ("pouch", "Check your Taels (currency)", ["money", "wealth"]),
        ]
    },
    "cultivation": {
        "name": "Cultivation & Training",
        "emoji": "🌀",
        "description": "Grow your power through Ki refinement and mastery.",
        "commands": [
            ("observe", "Meditate to gain Ki and Mastery", []),
            ("comprehend", "Deeply study your technique for massive Mastery", []),
            ("pavilion", "Choose or view your active technique", ["pav"]),
            ("techniques", "List all available techniques", ["techs"]),
            ("reset_technique", "Abandon your current technique (costs 500 Taels)", []),
            ("breakthrough", "Attempt to reach the next Major Realm", ["bt"]),
            ("breakthrough_status", "Check breakthrough progress and bonuses", ["btst"]),
        ]
    },
    "combat": {
        "name": "Combat & Warfare",
        "emoji": "⚔️",
        "description": "Test your strength against beasts and rivals.",
        "commands": [
            ("hunt", "Hunt spirit beasts for rewards", ["h"]),
            ("spar", "Challenge another player to a friendly duel", []),
            ("huntleaderboard", "View hunting statistics leaderboards", ["hlb"]),
        ]
    },
    "inventory": {
        "name": "Inventory & Shop",
        "emoji": "🎒",
        "description": "Manage your items and trade with merchants.",
        "commands": [
            ("inventory", "View all items in your possession", ["inv"]),
            ("use", "Consume an item from your inventory", []),
            ("bazaar", "Browse the market for goods", ["bz"]),
            ("buy", "Purchase an item from a shop", []),
            ("sell", "Sell an item from your inventory", []),
            ("give", "Give an item to another player", []),
            ("search", "Find which shop sells a specific item", []),
        ]
    },
    "daily": {
        "name": "Daily Actions & Recovery",
        "emoji": "🏮",
        "description": "Earn resources, recover, and maintain your cultivation.",
        "commands": [
            ("work", "Perform labor to earn Taels", []),
            ("recover", "Meditate to restore Vitality and Ki", []),
            ("cancel", "Cancel an ongoing meditation session", []),
            ("meditate", "Check your next heartbeat/regeneration", []),
            ("focus", "Convert Vitality into Ki", []),
            ("rest", "Instantly restore HP and Vitality", []),
            ("toggle_dm", "Enable or disable heartbeat direct messages", []),
        ]
    }
}


# ==========================================
# COMMAND INFORMATION RETRIEVAL
# ==========================================

def get_all_command_names() -> List[str]:
    """
    Get a list of all command names across all categories.
    
    Returns:
        List[str]: List of command names
    
    Example:
        >>> commands = get_all_command_names()
        >>> print(commands[:5])
        ['start', 'stats', 'profile', 'pstatus', 'afk']
    """
    commands = []
    for category in CATEGORIES.values():
        for cmd_name, _, _ in category["commands"]:
            commands.append(cmd_name)
    return commands


def get_command_info(command_name: str) -> Optional[Dict]:
    """
    Get detailed information about a specific command.
    
    Args:
        command_name: Name of the command to look up
        
    Returns:
        Optional[Dict]: Dictionary with command info, or None if not found
        {
            "name": "hunt",
            "description": "Hunt spirit beasts",
            "aliases": ["h"],
            "category": "combat",
            "category_name": "Combat & Warfare",
            "example": "!hunt"
        }
    """
    command_name_lower = command_name.lower()
    
    for category_key, category_data in CATEGORIES.items():
        for cmd_name, description, aliases in category_data["commands"]:
            if cmd_name == command_name_lower:
                return {
                    "name": cmd_name,
                    "description": description,
                    "aliases": aliases,
                    "category": category_key,
                    "category_name": category_data["name"],
                    "category_emoji": category_data["emoji"],
                    "example": f"!{cmd_name}"
                }
            
            # Also check if the command name is actually an alias
            if command_name_lower in aliases:
                return {
                    "name": cmd_name,
                    "description": description,
                    "aliases": aliases,
                    "category": category_key,
                    "category_name": category_data["name"],
                    "category_emoji": category_data["emoji"],
                    "example": f"!{cmd_name}"
                }
    
    return None


def get_category_commands(category_key: str) -> List[Tuple[str, str, List[str]]]:
    """
    Get all commands for a specific category.
    
    Args:
        category_key: The category key (e.g., "combat", "genesis")
        
    Returns:
        List[Tuple[str, str, List[str]]]: List of (command_name, description, aliases)
    """
    category = CATEGORIES.get(category_key)
    if category:
        return category["commands"]
    return []


async def get_command_cooldown(bot, command_name: str) -> Optional[int]:
    """
    Get the cooldown for a specific command from bot settings.
    
    Args:
        bot: The bot instance
        command_name: Name of the command
        
    Returns:
        Optional[int]: Cooldown in seconds, or None if no custom cooldown
    """
    try:
        # Check if there's a custom cooldown set in bot_settings
        cooldown_key = f"cooldown_{command_name.lower()}"
        cooldown = await get_bot_setting(bot.db, cooldown_key)
        
        if cooldown and isinstance(cooldown, int):
            return cooldown
        
        # Default cooldowns based on command type
        default_cooldowns = {
            "hunt": 600,
            "spar": 30,
            "work": 5,
            "observe": 5,
            "comprehend": 1800,  # 30 minutes
            "recover": 300,
            "focus": 300,
        }
        
        return default_cooldowns.get(command_name.lower())
    except Exception:
        return None


# ==========================================
# HELP SELECT DROPDOWN
# ==========================================

class HelpSelect(Select):
    """
    Dropdown menu for selecting help categories.
    
    This creates a select menu with all available categories
    that users can choose from to view command lists.
    """
    
    def __init__(self, member_id: int, bot):
        """
        Initialize the help dropdown.
        
        Args:
            member_id: Discord user ID (to verify interaction)
            bot: Bot instance for database access
        """
        self.member_id = member_id
        self.bot = bot
        
        # Build options from CATEGORIES
        options = []
        for category_key, category_data in CATEGORIES.items():
            option = discord.SelectOption(
                label=category_data["name"],
                description=category_data["description"][:100],  # Discord limit
                emoji=category_data["emoji"],
                value=category_key  # Store the key, not the display name
            )
            options.append(option)
        
        super().__init__(
            placeholder="Choose a category to study...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """
        Handle dropdown selection.
        
        When a user selects a category, this sends the appropriate
        category embed with all commands in that category.
        """
        # Verify this is the right user
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                config.MSG_HELP_ALREADY_VIEWING,
                ephemeral=True
            )
            return
        
        # Get selected category
        selected_key = self.values[0]
        category_data = CATEGORIES.get(selected_key)
        
        if not category_data:
            await interaction.response.send_message(
                "❌ Category not found.",
                ephemeral=True
            )
            return
        
        # Build and send the category embed
        embed = category_embed(
            category_name=category_data["name"],
            category_emoji=category_data["emoji"],
            commands_list=category_data["commands"],
            category_description=category_data["description"]
        )
        
        await interaction.response.edit_message(embed=embed)


# ==========================================
# HELP VIEW (Main view with dropdown + buttons)
# ==========================================

class HelpView(View):
    """
    Main help view containing the category dropdown.
    
    This view is attached to the main help menu and allows
    users to browse command categories.
    """
    
    def __init__(self, member_id: int, bot):
        """
        Initialize the help view.
        
        Args:
            member_id: Discord user ID
            bot: Bot instance
        """
        super().__init__(timeout=120)  # 2 minute timeout (longer for help)
        self.member_id = member_id
        self.bot = bot
        
        # Add the dropdown menu
        self.add_item(HelpSelect(member_id, bot))
    
    async def on_timeout(self):
        """Clean up when view times out - disable all children."""
        for child in self.children:
            child.disabled = True
        
        # Try to edit the original message to show it expired
        if hasattr(self, 'message'):
            try:
                embed = discord.Embed(
                    title="⏳ Help Menu Expired",
                    description="The help menu has timed out. Type `!help` again to open a new one.",
                    color=format_embed_color("error")
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass


# ==========================================
# COMMAND DETAIL VIEW (for !help <command>)
# ==========================================

class CommandDetailView(View):
    """
    View for command details with back button to return to help menu.
    """
    
    def __init__(self, member_id: int, bot, original_ctx):
        """
        Initialize the command detail view.
        
        Args:
            member_id: Discord user ID
            bot: Bot instance
            original_ctx: Original context (to regenerate help menu)
        """
        super().__init__(timeout=60)
        self.member_id = member_id
        self.bot = bot
        self.original_ctx = original_ctx
    
    @discord.ui.button(label="← Back to Help Menu", style=discord.ButtonStyle.secondary, emoji="📚")
    async def back_button(self, interaction: discord.Interaction, button: Button):
        """
        Return to the main help menu.
        """
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "❌ This help session belongs to someone else.",
                ephemeral=True
            )
            return
        
        from commands.help import show_help_menu
        
        # Show the main help menu again
        await show_help_menu(self.original_ctx, interaction)


# ==========================================
# HELPER: Check if help feature is enabled
# ==========================================

async def is_help_enabled(bot) -> bool:
    """
    Check if the help feature is enabled in bot settings.
    
    Args:
        bot: Bot instance
        
    Returns:
        bool: True if enabled, False otherwise
    """
    return await get_bot_setting(bot.db, "toggle_help", True)


# ==========================================
# HELPER: Get category suggestion for command
# ==========================================

def suggest_category_for_command(command_name: str) -> Optional[str]:
    """
    Suggest which category a command belongs to.
    
    This is useful for the !help <command> response to show
    where the user can find similar commands.
    
    Args:
        command_name: Name of the command
        
    Returns:
        Optional[str]: Category key or None if not found
    """
    for category_key, category_data in CATEGORIES.items():
        for cmd_name, _, _ in category_data["commands"]:
            if cmd_name == command_name:
                return category_key
    return None


print("[DEBUG] help_helpers.py: Help helpers loaded successfully")