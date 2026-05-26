"""
commands/pavilion.py - Command logic for Pavilion cog
Contains all command implementations for technique selection and management.

This file handles:
- !pavilion - Visit the Pavilion to choose a technique
- !techniques - List all available techniques
- !reset_technique - Abandon current technique for a new path

All embeds are imported from embeds.pavilion_embeds.
All helpers and views are imported from backend.pavilion_helpers.
"""

import discord
from discord.ext import commands
from typing import Optional

# Backend imports
from backend.db import get_bot_setting, is_user_banned
from backend.pavilion_helpers import (
    get_all_techniques,
    get_available_techniques_for_rank,
    get_technique_data,
    meets_rank_requirement,
    validate_technique_exists,
    PavilionView,
    ResetConfirmView
)
from backend.constants import TECHNIQUES

# Embed imports
from embeds.pavilion_embeds import (
    pavilion_main_embed,
    current_technique_embed,
    techniques_list_embed,
    insufficient_ki_embed,
    rank_requirement_embed,
    reset_not_possible_embed,
    no_technique_to_reset_embed,
    already_meditating_embed,
    feature_disabled_embed
)

import config

print("[DEBUG] commands/pavilion.py: Loading Pavilion commands...")


# ==========================================
# MAIN COG
# ==========================================

class Pavilion(commands.Cog):
    """
    Pavilion cog - Handles technique selection and management.
    
    Features:
    - Browse and select martial techniques
    - View all available techniques with descriptions
    - Reset current technique to choose a new path (costs Taels)
    
    Commands:
    - !pavilion / !pav - Visit the Pavilion of Hidden Scrolls
    - !techniques / !techs - List all available techniques
    - !reset_technique / !resettech - Abandon current technique
    """
    
    def __init__(self, bot):
        """
        Initialize the Pavilion cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        print("[DEBUG] Pavilion cog initialized")
    
    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if pavilion feature is enabled.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        enabled = await get_bot_setting(self.bot.db, "toggle_pavilion", True)
        if not enabled:
            embed = feature_disabled_embed()
            await ctx.send(embed=embed, ephemeral=True)
        return enabled
    
    async def _get_user_or_error(self, ctx: commands.Context, user_id: int):
        """
        Fetch user from database or send error.
        
        Args:
            ctx: Command context
            user_id: Discord user ID
            
        Returns:
            dict or None: User document if found, None otherwise
        """
        user = await self.bot.db.users.find_one({"user_id": user_id})
        if not user:
            await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)
            return None
        return user
    
    # ==========================================
    # COMMAND: PAVILION
    # ==========================================
    
    @commands.hybrid_command(
        name="pavilion",
        aliases=["pav"],
        description="Visit the Pavilion of Hidden Scrolls to choose a martial technique"
    )
    async def pavilion(self, ctx: commands.Context):
        """
        Visit the Pavilion to choose a martial technique.
        
        Requirements:
        - Must be registered
        - Must have 100 Ki (Mortal rank only)
        - Cannot be meditating
        - Cannot already have a technique (use !reset_technique first)
        
        Usage: !pavilion or !pav
        """
        print(f"[DEBUG] pavilion.pavilion: Called by {ctx.author.id}")
        
        # Feature and ban checks
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        user_id = ctx.author.id
        
        # Check if user is meditating
        if hasattr(self.bot, 'is_meditating') and user_id in self.bot.is_meditating:
            embed = already_meditating_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Fetch user data
        user = await self._get_user_or_error(ctx, user_id)
        if not user:
            return
        
        rank = user.get("rank", "The Bound (Mortal)")
        ki = user.get("ki", 0)
        active_tech = user.get("active_tech", "None")
        mastery = user.get("mastery", 0.0)
        
        # Check Ki requirement for Mortal rank
        if "Mortal" in rank and ki < 100:
            embed = insufficient_ki_embed(ki, 100)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # If user already has a technique, show current instead
        if active_tech != "None":
            embed = current_technique_embed(active_tech, mastery, 500)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Get available techniques for this rank
        available_techs = get_available_techniques_for_rank(rank)
        
        if not available_techs:
            await ctx.send(
                "❌ No techniques are available for your current rank.\n"
                "Continue your cultivation to unlock new techniques.",
                ephemeral=True
            )
            return
        
        # Create and send the pavilion view
        view = PavilionView(ctx, user_id, self.bot, available_techs, rank)
        embed = pavilion_main_embed(rank, ki, 100, False)
        
        message = await ctx.send(embed=embed, view=view)
        view.message = message  # Store message for timeout handling
    
    # ==========================================
    # COMMAND: TECHNIQUES
    # ==========================================
    
    @commands.hybrid_command(
        name="techniques",
        aliases=["techs"],
        description="List all available martial techniques"
    )
    async def list_techniques(self, ctx: commands.Context):
        """
        Display a list of all available techniques with descriptions.
        
        Shows:
        - Technique name
        - Type (Movement, Strike, Defense, etc.)
        - Family (Orthodox, Unorthodox, Demonic)
        - Effect description
        - Rank requirement
        
        Usage: !techniques or !techs
        """
        print(f"[DEBUG] pavilion.list_techniques: Called by {ctx.author.id}")
        
        # Feature and ban checks
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        # Get all techniques
        techniques = get_all_techniques()
        
        if not techniques:
            await ctx.send("❌ No techniques are available at this time.", ephemeral=True)
            return
        
        embed = techniques_list_embed(techniques)
        await ctx.send(embed=embed)
    
    # ==========================================
    # COMMAND: RESET TECHNIQUE
    # ==========================================
    
    @commands.hybrid_command(
        name="reset_technique",
        aliases=["resettech"],
        description="Abandon your current technique and start a new path (costs 500 Taels)"
    )
    async def reset_technique(self, ctx: commands.Context):
        """
        Reset your current technique to choose a new one.
        
        Cost: 500 Taels
        Effect: Lost all mastery progress on current technique
        
        Usage: !reset_technique or !resettech
        """
        print(f"[DEBUG] pavilion.reset_technique: Called by {ctx.author.id}")
        
        # Feature and ban checks
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        user_id = ctx.author.id
        
        # Fetch user data
        user = await self._get_user_or_error(ctx, user_id)
        if not user:
            return
        
        active_tech = user.get("active_tech", "None")
        mastery = user.get("mastery", 0.0)
        taels = user.get("taels", 0)
        
        RESET_COST = 500
        
        # Check if user has a technique to reset
        if active_tech == "None":
            embed = no_technique_to_reset_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Check if user has enough Taels
        if taels < RESET_COST:
            embed = reset_not_possible_embed(taels, RESET_COST)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Create confirmation view
        view = ResetConfirmView(
            member_id=user_id,
            bot=self.bot,
            tech_name=active_tech,
            mastery=mastery,
            reset_cost=RESET_COST,
            current_taels=taels
        )
        
        from embeds.pavilion_embeds import reset_confirmation_embed
        embed = reset_confirmation_embed(active_tech, mastery, RESET_COST)
        
        message = await ctx.send(embed=embed, view=view)
        view.message = message  # Store message for timeout handling


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Pavilion(bot))
    print("[DEBUG] commands/pavilion.py: Setup complete")