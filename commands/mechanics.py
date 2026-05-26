"""
commands/mechanics.py - Command logic for Mechanics cog
Contains all command implementations for meditation, focus, rest, and heartbeat.

This file handles:
- !meditate (was !recover) - 60-second meditation to restore Vit/Ki
- !cancel - Cancel active meditation
- !heartbeat / !hb - Check next heartbeat and player stats
- !focus - Convert Vitality to Ki
- !rest - Instantly restore HP and Vitality
- !toggle_dm - Toggle heartbeat DMs

All embeds are imported from embeds.mechanics_embeds.
All state management is imported from backend.mechanics_helpers.
"""

import asyncio
import datetime
from typing import Optional

import discord
from discord.ext import commands

# Backend imports
from backend.db import get_bot_setting, is_user_banned
from backend.helpers import get_max_stats
from backend.mechanics_helpers import (
    MechanicsState,
    is_mechanics_enabled,
    format_cooldown_time,
    get_utc_now
)
from backend.constants import (
    HEARTBEAT_REGEN,
    RECOVER_VIT_GAIN_BASE,
    RECOVER_KI_GAIN_BASE,
    RECOVER_VIT_HERMIT_BONUS,
    RECOVER_KI_HERMIT_BONUS,
    RECOVER_DURATION_SECONDS,
    RECOVER_COOLDOWN_MINUTES,
    CANCEL_PENALTY_THRESHOLD_SECONDS,
    CANCEL_PENALTY_MINUTES,
    FOCUS_VIT_COST,
    FOCUS_KI_GAIN,
    FOCUS_COOLDOWN_MINUTES,
    REST_HP_GAIN,
    REST_VIT_GAIN,
    REST_COOLDOWN_HOURS
)

# Embed imports
from embeds.mechanics_embeds import (
    meditation_start_embed,
    meditation_progress_embed,
    meditation_complete_embed,
    meditation_cancelled_embed,
    not_meditating_embed,
    cooldown_embed,
    focus_embed,
    low_vitality_embed,
    rest_embed,
    toggle_dm_embed,
    heartbeat_status_embed,
    heartbeat_not_ready_embed,
    mechanics_disabled_embed,
    not_registered_embed,
    already_meditating_embed
)

import config

print("[DEBUG] commands/mechanics.py: Loading Mechanics commands...")


# ==========================================
# MAIN COG
# ==========================================

class Mechanics(commands.Cog):
    """
    Mechanics cog - Handles meditation, recovery, focus, rest, and heartbeat.
    
    Features:
    - 60-second meditation for Vitality/Ki recovery
    - Focus to convert Vitality to Ki
    - Rest for instant HP/Vitality restoration
    - 20-minute heartbeat regen for all players
    - DM toggling for heartbeat notifications
    
    Commands:
    - !meditate - Enter 60-second meditation
    - !cancel - Cancel active meditation
    - !heartbeat / !hb - Check next heartbeat and your stats
    - !focus - Convert Vitality to Ki
    - !rest - Instantly restore HP/Vitality
    - !toggle_dm - Toggle heartbeat DMs
    """
    
    def __init__(self, bot):
        """
        Initialize the Mechanics cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.state = MechanicsState(bot)
        
        # Start heartbeat task
        self.bot.loop.create_task(self._start_heartbeat())
        
        # Sync with bot's meditation tracking if exists
        if not hasattr(self.bot, "is_meditating"):
            self.bot.is_meditating = set()
        
        print("[DEBUG] Mechanics cog initialized")
    
    async def _start_heartbeat(self):
        """Start the heartbeat manager after bot is ready."""
        await self.bot.wait_until_ready()
        await self.state.start_heartbeat()
    
    async def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.state.stop_heartbeat()
    
    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if mechanics feature is enabled.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        if not await is_mechanics_enabled(self.bot):
            embed = mechanics_disabled_embed()
            await ctx.send(embed=embed, ephemeral=True)
            return False
        return True
    
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
    # COMMAND: MEDITATE (was recover)
    # ==========================================
    
    @commands.hybrid_command(
        name="meditate",
        aliases=["recover", "med"],
        description="Meditate for 60 seconds to restore Vitality and Ki"
    )
    async def meditate(self, ctx: commands.Context):
        """
        Enter a 60-second meditation session.
        
        Restores:
        - Base: 25 Vitality, 5 Ki
        - Hermit bonus: +10 Vitality, +10 Ki (total 35/15)
        
        Cooldown: 5 minutes after completion
        Cancellation penalty: 2-minute cooldown if cancelled within 30 seconds
        
        Usage: !meditate
        """
        print(f"[DEBUG] mechanics.meditate: Called by {ctx.author.id}")
        
        # Feature and ban checks
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        user_id = ctx.author.id
        
        # Check cooldown
        cooldown_remaining = self.state.get_meditate_cooldown(user_id)
        if cooldown_remaining is not None:
            embed = cooldown_embed("meditate", cooldown_remaining)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Check if already meditating
        if self.state.is_meditating(user_id):
            embed = already_meditating_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Fetch user data
        user = await self._get_user_or_error(ctx, user_id)
        if not user:
            return
        
        # Start meditation
        self.state.start_meditation(user_id)
        self.bot.is_meditating.add(user_id)
        
        # Send start message
        embed = meditation_start_embed()
        msg = await ctx.send(embed=embed)
        
        # Meditation loop (updates every 10 seconds)
        total_time = RECOVER_DURATION_SECONDS
        elapsed = 0
        cancelled = False
        
        while elapsed < total_time:
            await asyncio.sleep(10)
            elapsed += 10
            
            # Check if cancelled
            if not self.state.is_meditating(user_id):
                cancelled = True
                break
            
            # Update progress bar
            remaining = total_time - elapsed
            embed = meditation_progress_embed(remaining, elapsed, total_time)
            await msg.edit(embed=embed)
        
        # Clean up meditation state
        self.state.cancel_meditation(user_id)
        self.bot.is_meditating.discard(user_id)
        
        if cancelled:
            return
        
        # Apply meditation rewards
        rank = user.get("rank", "The Bound (Mortal)")
        background = user.get("background", "")
        is_hermit = (background == "Hermit")
        
        # Calculate gains
        vit_gain = RECOVER_VIT_GAIN_BASE
        ki_gain = RECOVER_KI_GAIN_BASE
        if is_hermit:
            vit_gain += RECOVER_VIT_HERMIT_BONUS
            ki_gain += RECOVER_KI_GAIN_BASE + RECOVER_KI_HERMIT_BONUS
        
        # Get current stats
        current_vit = user.get("vitality", 0)
        current_ki = user.get("ki", 0)
        max_stats = get_max_stats(rank)
        
        new_vit = min(max_stats["max_vit"], current_vit + vit_gain)
        new_ki = min(max_stats["ki_cap"], current_ki + ki_gain)
        
        # Update database
        await self.bot.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"vitality": new_vit, "ki": new_ki}}
        )
        
        # Set cooldown (5 minutes)
        self.state.set_meditate_cooldown(user_id, RECOVER_COOLDOWN_MINUTES * 60)
        
        # Send completion embed
        embed = meditation_complete_embed(
            vit_gain=vit_gain,
            ki_gain=ki_gain,
            new_vit=new_vit,
            new_ki=new_ki,
            max_vit=max_stats["max_vit"],
            max_ki=max_stats["ki_cap"],
            is_hermit=is_hermit
        )
        await msg.edit(embed=embed)
    
    # ==========================================
    # COMMAND: CANCEL
    # ==========================================
    
    @commands.hybrid_command(
        name="cancel",
        description="Cancel your active meditation session"
    )
    async def cancel_meditation(self, ctx: commands.Context):
        """
        Cancel an ongoing meditation session.
        
        Penalty: If cancelled within 30 seconds of starting,
        applies a 2-minute cooldown.
        
        Usage: !cancel
        """
        print(f"[DEBUG] mechanics.cancel_meditation: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        
        user_id = ctx.author.id
        
        if not self.state.is_meditating(user_id):
            embed = not_meditating_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Check if penalty applies (cancelled within 30 seconds)
        elapsed = self.state.get_meditation_elapsed(user_id) or 0
        penalty_applied = elapsed < CANCEL_PENALTY_THRESHOLD_SECONDS
        
        if penalty_applied:
            self.state.set_meditate_cooldown(user_id, CANCEL_PENALTY_MINUTES * 60)
        
        # Cancel meditation
        self.state.cancel_meditation(user_id)
        self.bot.is_meditating.discard(user_id)
        
        embed = meditation_cancelled_embed(penalty_applied, CANCEL_PENALTY_MINUTES)
        await ctx.send(embed=embed, ephemeral=True)
    
    # ==========================================
    # COMMAND: HEARTBEAT (was meditate_status)
    # ==========================================
    
    @commands.hybrid_command(
        name="heartbeat",
        aliases=["hb"],
        description="Check when the next heartbeat recovery occurs and view your stats"
    )
    async def heartbeat_status(self, ctx: commands.Context):
        """
        Display the next heartbeat time and your current stats.
        
        Heartbeat restores HP and Vitality every 20 minutes.
        
        Usage: !heartbeat or !hb
        """
        print(f"[DEBUG] mechanics.heartbeat_status: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        
        user_id = ctx.author.id
        
        # Get next heartbeat time
        next_heartbeat = self.state.heartbeat.get_next_heartbeat()
        if not next_heartbeat:
            embed = heartbeat_not_ready_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Calculate time remaining
        now = get_utc_now()
        time_left = next_heartbeat - now
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)
        
        # Fetch user data
        user = await self._get_user_or_error(ctx, user_id)
        if not user:
            return
        
        rank = user.get("rank", "The Bound (Mortal)")
        hp = user.get("hp", 0)
        vit = user.get("vitality", 0)
        ki = user.get("ki", 0)
        
        max_stats = get_max_stats(rank)
        regen = HEARTBEAT_REGEN.get(rank, 25)
        
        # Check meditate cooldown for display
        meditate_cd = self.state.get_meditate_cooldown(user_id)
        meditate_cd_text = ""
        if meditate_cd:
            meditate_cd_text = f"⏳ `!meditate` ready in **{format_cooldown_time(meditate_cd)}**"
        
        embed = heartbeat_status_embed(
            minutes_left=minutes,
            seconds_left=seconds,
            regen_amount=regen,
            hp=hp,
            hp_cap=max_stats["max_hp"],
            vit=vit,
            vit_cap=max_stats["max_vit"],
            ki=ki,
            ki_cap=max_stats["ki_cap"],
            meditate_cd_text=meditate_cd_text
        )
        await ctx.send(embed=embed, ephemeral=True)
    
    # ==========================================
    # COMMAND: FOCUS
    # ==========================================
    
    @commands.hybrid_command(
        name="focus",
        description="Convert 10 Vitality into 5 Ki (5 minute cooldown)"
    )
    async def focus(self, ctx: commands.Context):
        """
        Convert Vitality into Ki.
        
        Cost: 10 Vitality
        Gain: 5 Ki
        Cooldown: 5 minutes
        
        Usage: !focus
        """
        print(f"[DEBUG] mechanics.focus: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        
        user_id = ctx.author.id
        
        # Check cooldown
        cooldown_remaining = self.state.get_focus_cooldown(user_id)
        if cooldown_remaining is not None:
            embed = cooldown_embed("focus", cooldown_remaining)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Fetch user data
        user = await self._get_user_or_error(ctx, user_id)
        if not user:
            return
        
        rank = user.get("rank", "The Bound (Mortal)")
        current_vit = user.get("vitality", 0)
        current_ki = user.get("ki", 0)
        
        # Check Vitality requirement
        if current_vit < FOCUS_VIT_COST:
            embed = low_vitality_embed(FOCUS_VIT_COST, current_vit)
            return await ctx.send(embed=embed, ephemeral=True)
        
        max_stats = get_max_stats(rank)
        new_vit = current_vit - FOCUS_VIT_COST
        new_ki = min(max_stats["ki_cap"], current_ki + FOCUS_KI_GAIN)
        
        # Update database
        await self.bot.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"vitality": new_vit, "ki": new_ki}}
        )
        
        # Set cooldown
        self.state.set_focus_cooldown(user_id, FOCUS_COOLDOWN_MINUTES * 60)
        
        embed = focus_embed(
            new_vit=new_vit,
            new_ki=new_ki,
            max_vit=max_stats["max_vit"],
            max_ki=max_stats["ki_cap"],
            vit_cost=FOCUS_VIT_COST,
            ki_gain=FOCUS_KI_GAIN
        )
        await ctx.send(embed=embed)
    
    # ==========================================
    # COMMAND: REST
    # ==========================================
    
    @commands.hybrid_command(
        name="rest",
        description="Instantly restore 10 HP and 10 Vitality (1 hour cooldown)"
    )
    async def rest(self, ctx: commands.Context):
        """
        Instantly restore HP and Vitality.
        
        Restores: +10 HP, +10 Vitality
        Cooldown: 1 hour
        
        Usage: !rest
        """
        print(f"[DEBUG] mechanics.rest: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        
        user_id = ctx.author.id
        
        # Check cooldown
        cooldown_remaining = self.state.get_rest_cooldown(user_id)
        if cooldown_remaining is not None:
            embed = cooldown_embed("rest", cooldown_remaining)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Fetch user data
        user = await self._get_user_or_error(ctx, user_id)
        if not user:
            return
        
        rank = user.get("rank", "The Bound (Mortal)")
        current_hp = user.get("hp", 0)
        current_vit = user.get("vitality", 0)
        
        max_stats = get_max_stats(rank)
        new_hp = min(max_stats["max_hp"], current_hp + REST_HP_GAIN)
        new_vit = min(max_stats["max_vit"], current_vit + REST_VIT_GAIN)
        
        # Update database
        await self.bot.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"hp": new_hp, "vitality": new_vit}}
        )
        
        # Set cooldown (1 hour)
        self.state.set_rest_cooldown(user_id, REST_COOLDOWN_HOURS * 3600)
        
        embed = rest_embed(
            new_hp=new_hp,
            new_vit=new_vit,
            max_hp=max_stats["max_hp"],
            max_vit=max_stats["max_vit"],
            hp_gain=REST_HP_GAIN,
            vit_gain=REST_VIT_GAIN
        )
        await ctx.send(embed=embed)
    
    # ==========================================
    # COMMAND: TOGGLE DM
    # ==========================================
    
    @commands.hybrid_command(
        name="toggle_dm",
        description="Enable or disable heartbeat recovery direct messages"
    )
    async def toggle_dm(self, ctx: commands.Context):
        """
        Toggle heartbeat DM notifications.
        
        When enabled, you'll receive a DM every 20 minutes
        showing how much HP and Vitality you regained.
        
        Usage: !toggle_dm
        """
        print(f"[DEBUG] mechanics.toggle_dm: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        
        user_id = ctx.author.id
        
        # Fetch user data
        user = await self._get_user_or_error(ctx, user_id)
        if not user:
            return
        
        current = user.get("heartbeat_dm", 1)
        new_value = 0 if current else 1
        
        await self.bot.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"heartbeat_dm": new_value}}
        )
        
        embed = toggle_dm_embed(new_value == 1)
        await ctx.send(embed=embed, ephemeral=True)


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Mechanics(bot))
    print("[DEBUG] commands/mechanics.py: Setup complete")