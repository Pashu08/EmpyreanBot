"""
commands/profile.py - Command logic for Profile cog
Contains the profile command implementation.

This file handles:
- !profile / !prof - View detailed character sheet (self or others)

All embeds are imported from embeds.profile_embeds.
All helpers are imported from backend.profile_helpers.
"""

import discord
from discord.ext import commands
from typing import Optional

# Backend imports
from backend.db import get_bot_setting, is_user_banned
from backend.profile_helpers import (
    get_background_emoji,
    get_background_perk,
    get_background_item,
    get_daily_bonus_status,
    get_milestone_progress,
    get_mastery_percentage,
    get_hidden_technique_hint,
    get_inventory_summary,
    get_profession_display
)

# Embed imports
from embeds.profile_embeds import (
    profile_embed,
    simple_profile_embed,
    not_registered_embed,
    feature_disabled_embed,
    user_not_found_embed,
    banned_user_embed
)

import config

print("[DEBUG] commands/profile.py: Loading Profile commands...")


# ==========================================
# MAIN COG
# ==========================================

class Profile(commands.Cog):
    """
    Profile cog - Displays detailed character sheets.
    
    Features:
    - View your own profile or other players' profiles
    - Shows background, profession, technique mastery
    - Displays daily bonus status
    - Shows inventory summary
    - Hidden technique hints
    
    Commands:
    - !profile / !prof [@member] - View character profile
    """
    
    def __init__(self, bot):
        """
        Initialize the Profile cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        print("[DEBUG] Profile cog initialized")
    
    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if profile feature is enabled.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        enabled = await get_bot_setting(self.bot.db, "toggle_profile", True)
        if not enabled:
            embed = feature_disabled_embed()
            await ctx.send(embed=embed, ephemeral=True)
        return enabled
    
    async def _fetch_user_data(self, user_id: int):
        """
        Fetch user data from database.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            dict or None: User document if found, None otherwise
        """
        return await self.bot.db.users.find_one({"user_id": user_id})
    
    # ==========================================
    # COMMAND: PROFILE
    # ==========================================
    
    @commands.hybrid_command(
        name="profile",
        aliases=["prof"],
        description="View detailed character sheet (yours or another player's)"
    )
    async def profile(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """
        Display a detailed character profile.
        
        Shows:
        - Background and perk
        - Starting item
        - Profession and rank
        - Wealth (Taels)
        - Daily bonus status (Work/Observe)
        - Active technique with mastery progress
        - Milestone progress (25/50/75/100%)
        - Hidden technique hints
        - Inventory summary
        
        Usage:
        - !profile - View your own profile
        - !profile @user - View another player's profile
        - !prof @user - Same as above (alias)
        """
        print(f"[DEBUG] profile.profile: Called by {ctx.author.id} for target {member.id if member else ctx.author.id}")
        
        # Feature toggle check
        if not await self._is_feature_enabled(ctx):
            return
        
        # Ban check for command user
        if await is_user_banned(self.bot.db, ctx.author.id):
            embed = banned_user_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Determine target
        target = member or ctx.author
        
        # Handle member not found (if member argument was invalid)
        if member and not target:
            embed = user_not_found_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Fetch user data from database
        user_data = await self._fetch_user_data(target.id)
        
        # If user not registered, show appropriate error
        if not user_data:
            # If looking up someone else, show their name
            if member:
                embed = not_registered_embed(target.display_name)
            else:
                embed = not_registered_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # ========== EXTRACT USER DATA ==========
        
        background = user_data.get("background", "Unknown")
        taels = user_data.get("taels", 0)
        active_tech = user_data.get("active_tech", "None")
        profession = user_data.get("profession", "None")
        profession_rank = user_data.get("prof_rank", "Apprentice")
        mastery_flags = user_data.get("mastery_flags")
        
        # ========== BACKGROUND DATA ==========
        bg_emoji = get_background_emoji(background)
        bg_perk = get_background_perk(background)
        bg_item = get_background_item(background)
        
        # ========== DAILY BONUS STATUS ==========
        work_avail, observe_avail, reset_hours, reset_minutes = get_daily_bonus_status(user_data)
        
        # ========== TECHNIQUE MASTERY ==========
        mastery_percent = get_mastery_percentage(user_data)
        milestones_reached, milestones_total = get_milestone_progress(active_tech, mastery_flags)
        hidden_hint = get_hidden_technique_hint(active_tech, mastery_flags, milestones_reached)
        
        # ========== PROFESSION DISPLAY ==========
        profession_display = get_profession_display(profession, profession_rank)
        
        # ========== INVENTORY SUMMARY ==========
        total_items, unique_items = await get_inventory_summary(self.bot.db, target.id)
        
        # ========== BUILD AND SEND EMBED ==========
        embed = profile_embed(
            target=target,
            background=background,
            background_emoji=bg_emoji,
            background_perk=bg_perk,
            background_item=bg_item,
            taels=taels,
            profession=profession_display,
            profession_rank=profession_rank,
            active_tech=active_tech,
            mastery_percent=mastery_percent,
            milestones_reached=milestones_reached,
            milestones_total=milestones_total,
            work_available=work_avail,
            observe_available=observe_avail,
            reset_hours=reset_hours,
            reset_minutes=reset_minutes,
            hidden_tech_hint=hidden_hint,
            total_items=total_items,
            unique_items=unique_items
        )
        
        await ctx.send(embed=embed)


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Profile(bot))
    print("[DEBUG] commands/profile.py: Setup complete")