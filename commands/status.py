"""
commands/status.py - Command logic for Status cog
"""

import discord
from discord.ext import commands
from typing import Optional

from backend.db import fetch_user, get_bot_setting, is_user_banned
from backend.status_helpers import (
    progress_bar,
    calculate_and_apply_afk_gains,
    get_background_emoji,
    get_meridian_status
)
from backend.helpers import get_max_stats, calculate_stage_from_ki
from embeds.status_embeds import (
    afk_no_gains_embed,
    afk_gains_embed,
    stats_embed
)
import config

print("[DEBUG] commands/status.py: Loading Status commands...")


class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Status cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_status", True)
        if not enabled:
            embed = discord.Embed(
                title="❌ Feature Disabled",
                description="The status system is currently disabled.",
                color=0xE74C3C
            )
            await ctx.send(embed=embed, ephemeral=True)
        return enabled

    @commands.hybrid_command(name="afk", aliases=["away"], description="Check your AFK gains.")
    async def afk(self, ctx):
        print(f"[DEBUG] status.afk: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        user_data = await fetch_user(self.bot.db, user_id)
        if not user_data:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        # Process AFK gains
        updated_data, gains, hours_passed = await calculate_and_apply_afk_gains(
            self.bot.db, user_id, user_data
        )

        if hours_passed <= 0:
            embed = afk_no_gains_embed()
        else:
            hours = int(hours_passed)
            minutes = int((hours_passed - hours) * 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            embed = afk_gains_embed(time_str, gains["ki"], gains["mastery"])

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="stats", aliases=["st"], description="View your core cultivation stats.")
    async def stats(self, ctx, member: Optional[discord.Member] = None):
        print(f"[DEBUG] status.stats: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        target = member or ctx.author
        user_data = await fetch_user(self.bot.db, target.id)
        if not user_data:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        # Apply AFK gains
        user_data, _, _ = await calculate_and_apply_afk_gains(
            self.bot.db, target.id, user_data
        )

        rank = user_data.get('rank', 'The Bound (Mortal)')
        max_stats = get_max_stats(rank)
        ki = user_data.get('ki', 0)
        stage = calculate_stage_from_ki(ki, max_stats['ki_cap'])
        
        bg = user_data.get('background', 'Unknown')
        bg_emoji = get_background_emoji(bg)
        taels = user_data.get('taels', 0)
        hp = user_data.get('hp', 0)
        vitality = user_data.get('vitality', 0)
        mastery = user_data.get('mastery', 0.0)
        combat_mastery = user_data.get('combat_mastery', 0)

        # Meridian status
        _, _, meridian_status = get_meridian_status(user_data.get('meridian_damage'))

        # Progress bars
        ki_bar = progress_bar(ki, max_stats['ki_cap'])
        mastery_bar = progress_bar(mastery, 100)

        embed = stats_embed(
            target=target,
            rank=rank,
            stage=stage,
            bg_emoji=bg_emoji,
            bg=bg,
            taels=taels,
            hp=hp,
            max_hp=max_stats['max_hp'],
            vitality=vitality,
            max_vit=max_stats['max_vit'],
            meridian_status=meridian_status,
            ki=ki,
            ki_cap=max_stats['ki_cap'],
            ki_bar=ki_bar,
            mastery=mastery,
            mastery_bar=mastery_bar,
            combat_mastery=combat_mastery
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Status(bot))
    print("[DEBUG] commands/status.py: Setup complete")