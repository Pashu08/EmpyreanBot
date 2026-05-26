"""
backend/pvp_helpers.py - Helper functions and UI views for PvP cog

This module handles:
- SparView class (battle UI with strike button)
- AcceptDeclineView class (challenge acceptance buttons)
- SparCooldownManager class (cooldown tracking)
- Damage calculation helper
- Bet validation helpers
"""

import discord
from discord.ui import View, Button
import datetime
import random
from typing import Dict, Optional, Tuple

from backend.helpers import format_embed_color
from backend.constants import PVP_DAMAGE_RANGE
from embeds.pvp_embeds import (
    spar_combat_embed,
    spar_result_embed,
    opponent_insufficient_taels_embed,
    challenge_expired_embed
)

print("[DEBUG] pvp_helpers.py: Loading PvP helpers...")


# ==========================================
# SPAR COOLDOWN MANAGER
# ==========================================

class SparCooldownManager:
    """
    Manages cooldowns for sparring.
    Players must wait 60 seconds between spars.
    """
    
    def __init__(self):
        """Initialize empty cooldown dictionary."""
        self._cooldowns: Dict[int, datetime.datetime] = {}
    
    def is_on_cooldown(self, user_id: int) -> Tuple[bool, int]:
        """
        Check if a user is on cooldown.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple[bool, int]: (is_on_cooldown, remaining_seconds)
        """
        cooldown_until = self._cooldowns.get(user_id)
        if not cooldown_until:
            return False, 0
        
        now = datetime.datetime.now()
        if now >= cooldown_until:
            # Cooldown expired, clean up
            del self._cooldowns[user_id]
            return False, 0
        
        remaining = int((cooldown_until - now).total_seconds())
        return True, remaining
    
    def set_cooldown(self, user_id: int, duration_seconds: int = 60):
        """
        Set a cooldown for a user.
        
        Args:
            user_id: Discord user ID
            duration_seconds: Cooldown duration (default 60 seconds)
        """
        self._cooldowns[user_id] = datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds)
    
    def clear_cooldown(self, user_id: int):
        """Manually clear a user's cooldown."""
        self._cooldowns.pop(user_id, None)


# ==========================================
# DAMAGE CALCULATION
# ==========================================

def calculate_spar_damage() -> int:
    """
    Calculate random damage for a spar strike.
    
    Returns:
        int: Random damage within PVP_DAMAGE_RANGE
    """
    return random.randint(PVP_DAMAGE_RANGE[0], PVP_DAMAGE_RANGE[1])


# ==========================================
# BET VALIDATION
# ==========================================

def validate_bet_amount(bet: int, user_taels: int, min_bet: int = 10, max_bet: int = 10000) -> Tuple[bool, str]:
    """
    Validate a bet amount.
    
    Args:
        bet: The bet amount to validate
        user_taels: User's current Taels
        min_bet: Minimum allowed bet (default 10)
        max_bet: Maximum allowed bet (default 10000)
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if bet < 0:
        return False, "Bet cannot be negative."
    
    if bet == 0:
        return True, None  # No bet is always valid
    
    if bet < min_bet:
        return False, f"Minimum bet is **{min_bet} Taels**."
    
    if bet > max_bet:
        return False, f"Maximum bet is **{max_bet} Taels**."
    
    if bet > user_taels:
        return False, f"You don't have enough Taels. You have {user_taels}, bet is {bet}."
    
    return True, None


def can_afford_bet(user_taels: int, bet_amount: int) -> bool:
    """
    Check if a user can afford a bet.
    
    Args:
        user_taels: User's current Taels
        bet_amount: Amount to check
        
    Returns:
        bool: True if user can afford, False otherwise
    """
    return user_taels >= bet_amount


# ==========================================
# ACCEPT/DECLINE VIEW
# ==========================================

class AcceptDeclineView(View):
    """
    View with Accept and Decline buttons for spar challenges.
    """
    
    def __init__(
        self,
        bot,
        challenger: discord.Member,
        opponent: discord.Member,
        bet_amount: int,
        challenger_hp: int,
        opponent_hp: int,
        pre_spar_stats: dict,
        timeout: int = 60
    ):
        """
        Initialize the accept/decline view.
        
        Args:
            bot: Bot instance
            challenger: The player who issued the challenge
            opponent: The player being challenged
            bet_amount: Amount of Taels bet
            challenger_hp: Challenger's HP
            opponent_hp: Opponent's HP
            pre_spar_stats: Original HP/Vitality stats to restore after
            timeout: Seconds until challenge expires (default 60)
        """
        super().__init__(timeout=timeout)
        self.bot = bot
        self.challenger = challenger
        self.opponent = opponent
        self.bet_amount = bet_amount
        self.challenger_hp = challenger_hp
        self.opponent_hp = opponent_hp
        self.pre_spar_stats = pre_spar_stats
        self.accepted = False
    
    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        """Handle accept button click."""
        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ Only the opponent can accept.", ephemeral=True)
            return
        
        # Check if opponent can afford the bet
        if self.bet_amount > 0:
            db = self.bot.db
            opponent_user = await db.users.find_one({"user_id": self.opponent.id})
            opponent_taels = opponent_user.get("taels", 0) if opponent_user else 0
            
            if opponent_taels < self.bet_amount:
                embed = opponent_insufficient_taels_embed(self.opponent.display_name, self.bet_amount)
                await interaction.response.edit_message(embed=embed, view=None)
                return
        
        self.accepted = True
        
        # Create the spar view
        spar_view = SparView(
            self.bot,
            self.challenger,
            self.opponent,
            self.challenger_hp,
            self.opponent_hp,
            self.bet_amount,
            self.pre_spar_stats
        )
        
        from embeds.pvp_embeds import spar_start_embed
        embed = spar_start_embed(self.challenger, self.opponent, self.bet_amount, self.challenger)
        
        await interaction.response.edit_message(content=None, embed=embed, view=spar_view)
        self.stop()
    
    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        """Handle decline button click."""
        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ Only the opponent can decline.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Spar Declined",
            description=f"{self.opponent.display_name} declined the spar challenge.",
            color=format_embed_color("error")
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def on_timeout(self):
        """Handle challenge timeout."""
        embed = challenge_expired_embed()
        
        # Try to edit the original message
        if hasattr(self, 'message'):
            try:
                await self.message.edit(embed=embed, view=None)
            except:
                pass
        self.stop()


# ==========================================
# SPAR VIEW (Battle UI)
# ==========================================

class SparView(View):
    """
    Main spar battle view with strike button.
    Handles turn-based combat between two players.
    """
    
    def __init__(
        self,
        bot,
        challenger: discord.Member,
        opponent: discord.Member,
        challenger_hp: int,
        opponent_hp: int,
        bet_amount: int,
        pre_spar_stats: dict
    ):
        """
        Initialize the spar view.
        
        Args:
            bot: Bot instance
            challenger: The player who initiated
            opponent: The opponent
            challenger_hp: Challenger's starting HP
            opponent_hp: Opponent's starting HP
            bet_amount: Amount of Taels bet
            pre_spar_stats: Original stats to restore after battle
        """
        super().__init__(timeout=180)  # 3 minute timeout for battle
        self.bot = bot
        self.challenger = challenger
        self.opponent = opponent
        self.challenger_hp = challenger_hp
        self.opponent_hp = opponent_hp
        self.challenger_max_hp = challenger_hp
        self.opponent_max_hp = opponent_hp
        self.turn = "challenger"  # challenger goes first
        self.combat_log = "The spar begins!"
        self.bet_amount = bet_amount
        self.pre_spar_stats = pre_spar_stats
        self.ended = False
    
    async def update_embed(self, interaction: discord.Interaction):
        """
        Update the battle embed with current HP and log.
        
        Args:
            interaction: The discord interaction
        """
        current_player = self.challenger if self.turn == "challenger" else self.opponent
        
        embed = spar_combat_embed(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_hp=self.challenger_hp,
            opponent_hp=self.opponent_hp,
            challenger_max_hp=self.challenger_max_hp,
            opponent_max_hp=self.opponent_max_hp,
            combat_log=self.combat_log,
            turn=self.turn,
            current_player=current_player
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except:
            await interaction.edit_original_response(embed=embed, view=self)
    
    async def end_spar(
        self,
        interaction: discord.Interaction,
        winner: discord.Member,
        loser: discord.Member
    ):
        """
        End the spar, restore stats, and handle bet payout.
        
        Args:
            interaction: The discord interaction
            winner: The winner of the spar
            loser: The loser of the spar
        """
        if self.ended:
            return
        self.ended = True
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        db = self.bot.db
        
        # Restore both players' original HP and Vitality
        for user_id, stats in self.pre_spar_stats.items():
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"hp": stats["hp"], "vitality": stats["vitality"]}}
            )
        
        winner_taels_gained = 0
        
        # Handle bet payout
        if self.bet_amount > 0:
            winner_user = await db.users.find_one({"user_id": winner.id})
            loser_user = await db.users.find_one({"user_id": loser.id})
            
            winner_taels = winner_user.get("taels", 0) if winner_user else 0
            loser_taels = loser_user.get("taels", 0) if loser_user else 0
            
            await db.users.update_one(
                {"user_id": loser.id},
                {"$set": {"taels": loser_taels - self.bet_amount}}
            )
            await db.users.update_one(
                {"user_id": winner.id},
                {"$set": {"taels": winner_taels + self.bet_amount}}
            )
            winner_taels_gained = self.bet_amount
        
        # Send result embed
        embed = spar_result_embed(
            winner=winner,
            loser=loser,
            combat_log=self.combat_log,
            bet_amount=self.bet_amount,
            winner_taels_gained=winner_taels_gained
        )
        
        await self.update_embed(interaction)
        self.stop()
    
    # ========== STRIKE BUTTON ==========
    
    @discord.ui.button(label="⚔️ Strike", style=discord.ButtonStyle.danger)
    async def strike_button(self, interaction: discord.Interaction, button: Button):
        """
        Handle strike button click.
        Deals random damage to the opponent and switches turns.
        """
        if self.ended:
            return
        
        # Check if it's the right user's turn
        if interaction.user not in (self.challenger, self.opponent):
            await interaction.response.send_message("❌ This is not your fight!", ephemeral=True)
            return
        
        if (self.turn == "challenger" and interaction.user != self.challenger):
            await interaction.response.send_message("⏳ Wait for your turn!", ephemeral=True)
            return
        
        if (self.turn == "opponent" and interaction.user != self.opponent):
            await interaction.response.send_message("⏳ Wait for your turn!", ephemeral=True)
            return
        
        # Calculate damage
        damage = calculate_spar_damage()
        
        # Apply damage based on whose turn it is
        if self.turn == "challenger":
            self.opponent_hp -= damage
            self.combat_log = f"{self.challenger.display_name} strikes for **{damage}** damage!"
            self.turn = "opponent"
        else:
            self.challenger_hp -= damage
            self.combat_log = f"{self.opponent.display_name} strikes for **{damage}** damage!"
            self.turn = "challenger"
        
        # Check for victory
        if self.challenger_hp <= 0:
            await self.end_spar(interaction, self.opponent, self.challenger)
        elif self.opponent_hp <= 0:
            await self.end_spar(interaction, self.challenger, self.opponent)
        else:
            await self.update_embed(interaction)
    
    async def on_timeout(self):
        """Handle battle timeout - auto-end the spar."""
        if self.ended:
            return
        self.ended = True
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        # Determine winner based on HP (higher HP wins if timeout)
        if self.challenger_hp > self.opponent_hp:
            winner = self.challenger
            loser = self.opponent
        elif self.opponent_hp > self.challenger_hp:
            winner = self.opponent
            loser = self.challenger
        else:
            # Tie - no winner, restore stats without bet transfer
            db = self.bot.db
            for user_id, stats in self.pre_spar_stats.items():
                await db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"hp": stats["hp"], "vitality": stats["vitality"]}}
                )
            
            embed = discord.Embed(
                title="⏳ Spar Timed Out",
                description="The spar took too long and ended in a draw. No Taels were exchanged.",
                color=format_embed_color("orange")
            )
            
            if hasattr(self, 'message'):
                try:
                    await self.message.edit(embed=embed, view=None)
                except:
                    pass
            self.stop()
            return
        
        # Restore stats and handle bet
        db = self.bot.db
        for user_id, stats in self.pre_spar_stats.items():
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"hp": stats["hp"], "vitality": stats["vitality"]}}
            )
        
        if self.bet_amount > 0:
            winner_user = await db.users.find_one({"user_id": winner.id})
            loser_user = await db.users.find_one({"user_id": loser.id})
            
            winner_taels = winner_user.get("taels", 0) if winner_user else 0
            loser_taels = loser_user.get("taels", 0) if loser_user else 0
            
            await db.users.update_one(
                {"user_id": loser.id},
                {"$set": {"taels": loser_taels - self.bet_amount}}
            )
            await db.users.update_one(
                {"user_id": winner.id},
                {"$set": {"taels": winner_taels + self.bet_amount}}
            )
        
        embed = spar_result_embed(
            winner=winner,
            loser=loser,
            combat_log="The spar timed out. The heavens declare a victor by health.",
            bet_amount=self.bet_amount,
            winner_taels_gained=self.bet_amount if self.bet_amount > 0 else 0
        )
        
        if hasattr(self, 'message'):
            try:
                await self.message.edit(embed=embed, view=None)
            except:
                pass
        self.stop()


print("[DEBUG] pvp_helpers.py: PvP helpers loaded successfully")