"""
commands/pvp.py - Command logic for PvP cog
Contains the main spar command implementation.

This file handles:
- !spar @user [bet] - Challenge another player to a spar

All embeds are imported from embeds.pvp_embeds.
All helpers and views are imported from backend.pvp_helpers.
"""

import discord
from discord.ext import commands
from typing import Optional

# Backend imports
from backend.db import get_bot_setting, is_user_banned
from backend.pvp_helpers import (
    SparCooldownManager,
    validate_bet_amount,
    AcceptDeclineView
)

# Embed imports
from embeds.pvp_embeds import (
    spar_challenge_embed,
    cannot_spar_self_embed,
    cannot_spar_bot_embed,
    rank_required_embed,
    already_meditating_embed,
    already_in_combat_embed,
    insufficient_taels_embed,
    min_bet_required_embed,
    bet_cannot_be_negative_embed,
    challenger_not_registered_embed,
    opponent_not_registered_embed,
    feature_disabled_embed,
    spar_cooldown_embed
)

import config

print("[DEBUG] commands/pvp.py: Loading PvP commands...")


# ==========================================
# MAIN COG
# ==========================================

class PvP(commands.Cog):
    """
    PvP cog - Handles player versus player sparring.
    
    Features:
    - Turn-based combat with strikes
    - Optional Taels betting
    - 60-second cooldown between spars
    - No permanent HP/Vitality loss
    
    Commands:
    - !spar @user [bet] - Challenge another player to a spar
    """
    
    def __init__(self, bot):
        """
        Initialize the PvP cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.cooldowns = SparCooldownManager()
        print("[DEBUG] PvP cog initialized")
    
    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if PvP feature is enabled.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        enabled = await get_bot_setting(self.bot.db, "toggle_pvp", True)
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
    
    async def _check_spar_requirements(
        self,
        ctx: commands.Context,
        opponent: discord.Member,
        bet: int
    ) -> tuple:
        """
        Check all requirements for sparring.
        
        Returns:
            tuple: (can_spar, error_embed, challenger_user, opponent_user)
        """
        # Check if users are registered
        challenger_user = await self._get_user_or_error(ctx, ctx.author.id)
        if not challenger_user:
            return False, None, None, None
        
        opponent_user = await self._get_user_or_error(ctx, opponent.id)
        if not opponent_user:
            embed = opponent_not_registered_embed(opponent.display_name)
            return False, embed, None, None
        
        # Check cooldown
        on_cd, remaining = self.cooldowns.is_on_cooldown(ctx.author.id)
        if on_cd:
            embed = spar_cooldown_embed(remaining)
            return False, embed, None, None
        
        # Check rank requirement (must be Third-Rate Warrior or higher)
        rank = challenger_user.get("rank", "The Bound (Mortal)")
        valid_ranks = ["Third-Rate Warrior", "Second-Rate Warrior", "First-Rate Warrior", "Peak Master"]
        if not any(r in rank for r in valid_ranks):
            embed = rank_required_embed()
            return False, embed, None, None
        
        # Check bet validation
        if bet > 0:
            author_taels = challenger_user.get("taels", 0)
            is_valid, error_msg = validate_bet_amount(bet, author_taels)
            if not is_valid:
                if "Minimum" in error_msg:
                    embed = min_bet_required_embed()
                elif "negative" in error_msg:
                    embed = bet_cannot_be_negative_embed()
                elif "don't have enough" in error_msg:
                    embed = insufficient_taels_embed(author_taels, bet)
                else:
                    embed = discord.Embed(
                        title="❌ Invalid Bet",
                        description=error_msg,
                        color=0xE74C3C
                    )
                return False, embed, None, None
        
        return True, None, challenger_user, opponent_user
    
    # ==========================================
    # COMMAND: SPAR
    # ==========================================
    
    @commands.hybrid_command(
        name="spar",
        description="Challenge another user to a friendly spar (with optional Taels bet)"
    )
    async def spar(
        self,
        ctx: commands.Context,
        opponent: discord.Member,
        bet: Optional[int] = 0
    ):
        """
        Challenge another player to a spar.
        
        How it works:
        - Turn-based combat with strikes
        - No permanent HP/Vitality loss (restored after)
        - Winner takes the bet (if any)
        - 60-second cooldown between spars
        
        Requirements:
        - Must be at least Third-Rate Warrior
        - Cannot spar yourself or a bot
        - Cannot be meditating or in combat
        - Bet minimum: 10 Taels (if betting)
        
        Usage:
        - !spar @user - Friendly spar, no bet
        - !spar @user 100 - Spar with 100 Taels bet
        """
        print(f"[DEBUG] pvp.spar: {ctx.author.id} challenged {opponent.id} with bet {bet}")
        
        # Feature toggle check
        if not await self._is_feature_enabled(ctx):
            return
        
        # Ban check
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        # Cannot spar yourself
        if opponent == ctx.author:
            embed = cannot_spar_self_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Cannot spar bots
        if opponent.bot:
            embed = cannot_spar_bot_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Check if opponent is banned
        if await is_user_banned(self.bot.db, opponent.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        # Check meditation status
        if hasattr(self.bot, 'is_meditating'):
            if ctx.author.id in self.bot.is_meditating:
                embed = already_meditating_embed()
                return await ctx.send(embed=embed, ephemeral=True)
            if opponent.id in self.bot.is_meditating:
                embed = already_meditating_embed(opponent.display_name)
                return await ctx.send(embed=embed, ephemeral=True)
        
        # Check combat status (hunting)
        if hasattr(self.bot, 'active_combats'):
            if ctx.author.id in self.bot.active_combats:
                embed = already_in_combat_embed()
                return await ctx.send(embed=embed, ephemeral=True)
            if opponent.id in self.bot.active_combats:
                embed = already_in_combat_embed(opponent.display_name)
                return await ctx.send(embed=embed, ephemeral=True)
        
        # Validate all spar requirements
        can_spar, error_embed, challenger_user, opponent_user = await self._check_spar_requirements(
            ctx, opponent, bet
        )
        
        if not can_spar:
            if error_embed:
                await ctx.send(embed=error_embed, ephemeral=True)
            return
        
        # Save pre-spar stats (HP and Vitality) for both players
        pre_spar_stats = {
            ctx.author.id: {
                "hp": challenger_user.get("hp", 100),
                "vitality": challenger_user.get("vitality", 100),
            },
            opponent.id: {
                "hp": opponent_user.get("hp", 100),
                "vitality": opponent_user.get("vitality", 100),
            },
        }
        
        # Get current HP for battle
        challenger_hp = pre_spar_stats[ctx.author.id]["hp"]
        opponent_hp = pre_spar_stats[opponent.id]["hp"]
        
        # Create challenge embed
        embed = spar_challenge_embed(ctx.author.display_name, opponent.mention, bet)
        
        # Create accept/decline view
        view = AcceptDeclineView(
            bot=self.bot,
            challenger=ctx.author,
            opponent=opponent,
            bet_amount=bet,
            challenger_hp=challenger_hp,
            opponent_hp=opponent_hp,
            pre_spar_stats=pre_spar_stats
        )
        
        # Send challenge message
        message = await ctx.send(embed=embed, view=view)
        view.message = message  # Store message reference for timeout handling


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(PvP(bot))
    print("[DEBUG] commands/pvp.py: Setup complete")