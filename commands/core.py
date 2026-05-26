"""
commands/core.py - Command logic for Core cog
Contains the main command implementations for character creation.

This file handles:
- !start command (main entry point for new players)
- Feature toggle checking
- Ban checking
- Integration with StartMenu view from backend.core_helpers

All embed designs are imported from embeds.core_embeds.
All UI views are imported from backend.core_helpers.
"""

import discord
from discord.ext import commands

# Backend imports
from backend.db import get_bot_setting, is_user_banned
from backend.core_helpers import StartMenu, is_core_enabled

# Embed imports
from embeds.core_embeds import (
    start_menu_embed,
    feature_disabled_embed,
    banned_user_embed,
    already_registered_embed
)

import config

print("[DEBUG] commands/core.py: Loading Core commands...")


# ==========================================
# MAIN COG
# ==========================================

class Core(commands.Cog):
    """
    Core cog - Handles character creation and basic bot functionality.
    
    Commands:
    - !start: Begin your journey by choosing a background
    """
    
    def __init__(self, bot):
        """
        Initialize the Core cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        print("[DEBUG] Core cog initialized")

    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if the core feature (character creation) is enabled.
        
        Sends an error message to the user if the feature is disabled.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        enabled = await get_bot_setting(self.bot.db, "toggle_core", True)
        
        if not enabled:
            embed = feature_disabled_embed("Character Creation")
            await ctx.send(embed=embed, ephemeral=True)
            
        return enabled

    # ==========================================
    # COMMAND: START
    # ==========================================
    
    @commands.hybrid_command(
        name="start",
        description="Begin your journey in the Murim world by choosing a background"
    )
    async def start(self, ctx: commands.Context):
        """
        Start command - Creates a new character for the user.
        
        This command:
        1. Checks if the feature is enabled
        2. Checks if the user is banned
        3. Checks if the user already has a character
        4. Displays the background selection menu (Laborer/Outcast/Hermit)
        
        Usage: !start
        
        The background choice is PERMANENT and cannot be changed later.
        """
        print(f"[DEBUG] core.start: Called by {ctx.author.id}")

        # ========== STEP 1: Check if feature is enabled ==========
        if not await self._is_feature_enabled(ctx):
            return

        # ========== STEP 2: Check if user is banned ==========
        if await is_user_banned(self.bot.db, ctx.author.id):
            embed = banned_user_embed()
            await ctx.send(embed=embed, ephemeral=True)
            return

        # ========== STEP 3: Check if user already has a character ==========
        existing = await self.bot.db.users.find_one({"user_id": ctx.author.id})
        if existing:
            embed = already_registered_embed()
            await ctx.send(embed=embed, ephemeral=True)
            return

        # ========== STEP 4: Display background selection menu ==========
        embed = start_menu_embed()
        view = StartMenu(ctx.author.id, self.bot)
        
        await ctx.send(embed=embed, view=view)
        
        print(f"[DEBUG] core.start: Start menu sent to {ctx.author.id}")


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """
    Setup function for loading the cog.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(Core(bot))
    print("[DEBUG] commands/core.py: Setup complete")