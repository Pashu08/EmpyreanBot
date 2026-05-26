"""
commands/help.py - Command logic for Help cog
Contains the main help command implementation.

This file handles:
- !help command (main help menu)
- !help <command> (command detail lookup)
- Integration with HelpView and CommandDetailView

All embeds are imported from embeds.help_embeds.
All helpers and views are imported from backend.help_helpers.
"""

import discord
from discord.ext import commands
from typing import Optional

# Backend imports
from backend.db import get_bot_setting, is_user_banned
from backend.help_helpers import (
    CATEGORIES,
    get_command_info,
    get_command_cooldown,
    is_help_enabled,
    suggest_category_for_command,
    HelpView,
    CommandDetailView
)

# Embed imports
from embeds.help_embeds import (
    main_help_embed,
    command_detail_embed,
    command_not_found_embed,
    help_disabled_embed,
    no_command_specified_embed
)

import config

print("[DEBUG] commands/help.py: Loading Help commands...")


# ==========================================
# HELPER FUNCTION: Show Help Menu
# ==========================================

async def show_help_menu(ctx: commands.Context, interaction: discord.Interaction = None):
    """
    Display the main help menu with category dropdown.
    
    This function is used both by the !help command and by the
    back button in command detail views.
    
    Args:
        ctx: Command context
        interaction: Optional interaction (if called from a button)
    """
    # Check if feature is enabled
    if not await is_help_enabled(ctx.bot):
        embed = help_disabled_embed()
        if interaction:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed, ephemeral=True)
        return
    
    # Create the main embed
    embed = main_help_embed()
    
    # Create the view with dropdown
    view = HelpView(ctx.author.id, ctx.bot)
    
    # Send or edit the message
    if interaction:
        # Coming from a button - edit the existing message
        await interaction.response.edit_message(embed=embed, view=view)
        # Store message reference for timeout handling
        view.message = interaction.message
    else:
        # First time - send new message
        message = await ctx.send(embed=embed, view=view)
        view.message = message


# ==========================================
# HELPER FUNCTION: Show Command Detail
# ==========================================

async def show_command_detail(ctx: commands.Context, command_name: str):
    """
    Display detailed information about a specific command.
    
    Args:
        ctx: Command context
        command_name: Name of the command to look up
    """
    # Check if feature is enabled
    if not await is_help_enabled(ctx.bot):
        embed = help_disabled_embed()
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    # Get command info
    cmd_info = get_command_info(command_name)
    
    if not cmd_info:
        # Command not found
        embed = command_not_found_embed(command_name)
        
        # Optional: Suggest similar commands
        suggested = suggest_category_for_command(command_name.lower())
        if suggested:
            category = CATEGORIES.get(suggested)
            if category:
                embed.description += f"\n\n💡 Did you mean to look in **{category['emoji']} {category['name']}**? Try `!help` to see all categories."
        
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    # Get cooldown if available
    cooldown = await get_command_cooldown(ctx.bot, cmd_info["name"])
    
    # Build usage example
    usage_example = cmd_info["example"]
    if cmd_info["aliases"] and len(cmd_info["aliases"]) > 0:
        # Show first alias as alternative example
        usage_example += f" (or !{cmd_info['aliases'][0]})"
    
    # Create the detailed embed
    embed = command_detail_embed(
        command_name=cmd_info["name"],
        description=cmd_info["description"],
        aliases=cmd_info["aliases"],
        usage_example=usage_example,
        cooldown=cooldown,
        long_description=None  # Can be expanded later
    )
    
    # Add category hint in footer
    embed.set_footer(
        text=f"Category: {cmd_info['category_emoji']} {cmd_info['category_name']} • "
             "Use the back button to return to the menu"
    )
    
    # Create view with back button
    view = CommandDetailView(ctx.author.id, ctx.bot, ctx)
    
    # Send the detailed embed
    await ctx.send(embed=embed, view=view)


# ==========================================
# MAIN COG
# ==========================================

class Help(commands.Cog):
    """
    Help cog - Provides interactive help system for players.
    
    Features:
    - Categorized command list with dropdown menu
    - Detailed command information with aliases and cooldowns
    - Back button navigation
    - Fully integrated with bot settings (can be toggled)
    
    Commands:
    - !help - Show main help menu
    - !help <command> - Show detailed info for a specific command
    """
    
    def __init__(self, bot):
        """
        Initialize the Help cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        
        # Remove the default help command to use our custom one
        if bot.get_command('help'):
            bot.remove_command('help')
        
        print("[DEBUG] Help cog initialized")
    
    async def cog_check(self, ctx: commands.Context) -> bool:
        """
        Global check for all commands in this cog.
        Ensures the user is not banned.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if user is not banned, False otherwise
        """
        if await is_user_banned(self.bot.db, ctx.author.id):
            await ctx.send(config.MSG_BANNED, ephemeral=True)
            return False
        return True
    
    # ==========================================
    # COMMAND: HELP
    # ==========================================
    
    @commands.hybrid_command(
        name="help",
        description="The complete manual for Empyrean Ascent.",
        aliases=["h", "commands", "manual"]
    )
    async def help(self, ctx: commands.Context, *, command: Optional[str] = None):
        """
        Display the interactive help system.
        
        Usage:
        - `!help` - Show main help menu with categories
        - `!help hunt` - Show detailed info about the hunt command
        - `!help h` - Same as above (using alias)
        
        Args:
            ctx: Command context
            command: Optional command name to get detailed info for
        """
        print(f"[DEBUG] help.help: Called by {ctx.author.id} with command='{command}'")
        
        # Check if feature is enabled (handled in helper functions)
        
        # Case 1: User wants help with a specific command
        if command:
            await show_command_detail(ctx, command)
            return
        
        # Case 2: User wants the main help menu
        await show_help_menu(ctx)
    
    # ==========================================
    # ERROR HANDLER FOR HELP COMMAND
    # ==========================================
    
    @help.error
    async def help_error(self, ctx: commands.Context, error: Exception):
        """
        Handle errors specific to the help command.
        
        Args:
            ctx: Command context
            error: The error that occurred
        """
        # If it's a missing argument, show the main menu
        if isinstance(error, commands.MissingRequiredArgument):
            await show_help_menu(ctx)
            return
        
        # Re-raise other errors to be handled by the global error handler
        raise error


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """
    Setup function for loading the cog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(Help(bot))
    print("[DEBUG] commands/help.py: Setup complete")