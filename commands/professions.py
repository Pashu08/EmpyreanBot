"""
commands/professions.py - Command logic for Professions cog
Contains all command implementations for profession selection and status viewing.

This file handles:
- !pchoose - Choose a profession or view available options
- !pstatus - View current profession progress and standing

All embeds are imported from embeds.professions_embeds.
All helpers are imported from backend.professions_helpers.
"""

import discord
from discord.ext import commands

# Backend imports
from backend.db import get_bot_setting, is_user_banned
from backend.professions_helpers import (
    PROFESSIONS_LIST,
    is_valid_profession,
    get_professions_list,
    validate_profession_choice,
    progress_bar
)

# Embed imports
from embeds.professions_embeds import (
    profession_list_embed,
    profession_chosen_embed,
    profession_status_embed,
    already_has_profession_embed,
    no_profession_embed,
    not_registered_embed,
    profession_not_found_embed,
    feature_disabled_embed
)

import config

print("[DEBUG] commands/professions.py: Loading Professions commands...")

# ==========================================
# MAIN COG
# ==========================================

class Professions(commands.Cog):
    """
    Professions cog - Handles profession selection and progression.

    Features:
    - Choose a permanent profession path
    - View profession progress and rank
    - Track experience points

    Commands:
    - !pchoose [profession] - Choose a profession or list available options
    - !pstatus - View your current profession standing
    """

    def __init__(self, bot):
        """
        Initialize the Professions cog.

        Args:
            bot: The bot instance
        """
        self.bot = bot
        print("[DEBUG] Professions cog initialized")

    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if professions feature is enabled.

        Args:
            ctx: Command context

        Returns:
            bool: True if enabled, False otherwise
        """
        enabled = await get_bot_setting(self.bot.db, "toggle_professions", True)
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
            embed = not_registered_embed()
            await ctx.send(embed=embed, ephemeral=True)
            return None
        return user

    # ==========================================
    # COMMAND: PCHOOSE
    # ==========================================

    @commands.hybrid_command(
        name="pchoose",
        description="Commit to a life-path profession"
    )
    async def pchoose(self, ctx: commands.Context, profession: str = None):
        """
        Choose a profession for your character.

        Professions available:
        - Alchemist - Expert in pill refining
        - Blacksmith - Master of weapon forging
        - Herb Gatherer - Skilled at finding herbs
        - Formation Master - Expert in combat formations
        - Instructor - Wise teacher of martial arts

        Usage:
        - !pchoose - Shows list of available professions
        - !pchoose Alchemist - Choose Alchemist as your profession

        Note: Profession choice is PERMANENT and cannot be changed.
        """
        print(f"[DEBUG] professions.pchoose: Called by {ctx.author.id}")

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

        current_prof = user.get("profession", "None")

        # Check if user already has a profession
        if current_prof != "None":
            embed = already_has_profession_embed(current_prof)
            return await ctx.send(embed=embed, ephemeral=True)

        # If no profession specified, show the list
        if profession is None:
            embed = profession_list_embed(get_professions_list())
            return await ctx.send(embed=embed, ephemeral=True)

        # Validate profession choice
        chosen = profession.title()
        is_valid, error_msg = validate_profession_choice(chosen)

        if not is_valid:
            embed = profession_not_found_embed(profession, get_professions_list())
            return await ctx.send(embed=embed, ephemeral=True)

        # Save the chosen profession to database
        await self.bot.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"profession": chosen}}
        )

        # Send confirmation
        embed = profession_chosen_embed(chosen)
        await ctx.send(embed=embed)

        print(f"[DEBUG] professions.pchoose: {ctx.author.id} chose {chosen}")

    # ==========================================
    # COMMAND: PSTATUS
    # ==========================================

    @commands.hybrid_command(
        name="pstatus",
        description="Check your professional standing and progress"
    )
    async def pstatus(self, ctx: commands.Context):
        """
        View your current profession progress.

        Shows:
        - Your chosen profession
        - Current rank (Apprentice)
        - Experience points and progress bar
        - Talent bonuses (placeholder)

        Usage: !pstatus
        """
        print(f"[DEBUG] professions.pstatus: Called by {ctx.author.id}")

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

        prof = user.get("profession", "None")
        rank = user.get("prof_rank", "Apprentice")
        xp = user.get("prof_xp", 0)
        req_xp = user.get("prof_req_xp", 1000)

        # Check if user has a profession
        if prof == "None":
            embed = no_profession_embed()
            return await ctx.send(embed=embed, ephemeral=True)

        # Generate progress bar
        bar, percent = progress_bar(xp, req_xp)

        # Send status embed
        embed = profession_status_embed(prof, rank, xp, req_xp, bar, percent)
        await ctx.send(embed=embed)


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Professions(bot))
    print("[DEBUG] commands/professions.py: Setup complete")