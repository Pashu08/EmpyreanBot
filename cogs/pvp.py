import discord
from discord.ext import commands
import random
import asyncio
import datetime
from utils.helpers import format_embed_color
from utils.db import get_bot_setting, is_user_banned, get_user_stat, update_user_stat
from utils.constants import PVP_DAMAGE_RANGE
import config

print("[DEBUG] pvp.py: Loading PvP cog...")

class SparView(discord.ui.View):
    def __init__(self, bot, challenger, opponent, challenger_hp, opponent_hp, bet_amount, pre_spar_stats):
        super().__init__(timeout=120)
        self.bot = bot
        self.challenger = challenger
        self.opponent = opponent
        self.challenger_hp = challenger_hp
        self.opponent_hp = opponent_hp
        self.turn = "challenger"  # challenger goes first
        self.log = "The spar begins!"
        self.bet_amount = bet_amount
        self.pre_spar_stats = pre_spar_stats  # Store original HP/Vit to restore later
        self.ended = False

    async def update_message(self, interaction, embed, view):
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except:
            await interaction.edit_original_response(embed=embed, view=view)

    async def end_spar(self, interaction, winner, loser):
        if self.ended:
            return
        self.ended = True

        # Restore both players' original HP and Vitality (no permanent loss)
        for user_id, stats in self.pre_spar_stats.items():
            await update_user_stat(self.bot.db, user_id, "hp", stats["hp"])
            await update_user_stat(self.bot.db, user_id, "vitality", stats["vitality"])

        # Handle Taels bet
        if self.bet_amount > 0:
            # Deduct from loser, add to winner
            loser_taels = await get_user_stat(self.bot.db, loser.id, "taels") or 0
            winner_taels = await get_user_stat(self.bot.db, winner.id, "taels") or 0
            await update_user_stat(self.bot.db, loser.id, "taels", loser_taels - self.bet_amount)
            await update_user_stat(self.bot.db, winner.id, "taels", winner_taels + self.bet_amount)
            bet_text = f"\n💰 {winner.display_name} won **{self.bet_amount} Taels**!"
        else:
            bet_text = ""

        embed = discord.Embed(
            title="⚔️ Spar Finished",
            description=f"**{winner.display_name}** defeated **{loser.display_name}**!\n{self.log}{bet_text}",
            color=format_embed_color("win") if winner == self.challenger else format_embed_color("lose")
        )
        for child in self.children:
            child.disabled = True
        await self.update_message(interaction, embed, self)
        self.stop()

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger)
    async def strike(self, interaction, button):
        if self.ended:
            return
        if interaction.user not in (self.challenger, self.opponent):
            return await interaction.response.send_message("❌ Not your fight!", ephemeral=True)
        if (self.turn == "challenger" and interaction.user != self.challenger) or (self.turn == "opponent" and interaction.user != self.opponent):
            return await interaction.response.send_message("⏳ Wait for your turn!", ephemeral=True)

        dmg = random.randint(PVP_DAMAGE_RANGE[0], PVP_DAMAGE_RANGE[1])
        if self.turn == "challenger":
            self.opponent_hp -= dmg
            self.log = f"{self.challenger.display_name} strikes for {dmg} damage!"
            self.turn = "opponent"
        else:
            self.challenger_hp -= dmg
            self.log = f"{self.opponent.display_name} strikes for {dmg} damage!"
            self.turn = "challenger"

        embed = discord.Embed(
            title=f"⚔️ Spar: {self.challenger.display_name} vs {self.opponent.display_name}",
            color=format_embed_color("main")
        )
        embed.add_field(name=f"{self.challenger.display_name}", value=f"❤️ HP: {max(0, self.challenger_hp)}", inline=True)
        embed.add_field(name=f"{self.opponent.display_name}", value=f"❤️ HP: {max(0, self.opponent_hp)}", inline=True)
        embed.add_field(name="📜 Combat Log", value=self.log, inline=False)

        if self.challenger_hp <= 0:
            await self.end_spar(interaction, self.opponent, self.challenger)
        elif self.opponent_hp <= 0:
            await self.end_spar(interaction, self.challenger, self.opponent)
        else:
            await self.update_message(interaction, embed, self)

class PvP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spar_cooldowns = {}  # user_id -> datetime
        print("[DEBUG] PvP cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_pvp", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="PvP"), ephemeral=True)
        return enabled

    async def _check_cooldown(self, user_id):
        """Check if user is on cooldown. Returns (is_on_cooldown, remaining_seconds)."""
        if user_id in self.spar_cooldowns:
            cooldown_until = self.spar_cooldowns[user_id]
            if datetime.datetime.now() < cooldown_until:
                remaining = int((cooldown_until - datetime.datetime.now()).total_seconds())
                return True, remaining
        return False, 0

    async def _set_cooldown(self, user_id):
        self.spar_cooldowns[user_id] = datetime.datetime.now() + datetime.timedelta(seconds=60)

    @commands.hybrid_command(name="spar", description="Challenge another user to a friendly spar (with optional Taels bet).")
    async def spar(self, ctx, opponent: discord.Member, bet: int = 0):
        print(f"[DEBUG] pvp.spar: {ctx.author.id} challenged {opponent.id} with bet {bet}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id) or await is_user_banned(self.bot.db, opponent.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        # Basic checks
        if opponent == ctx.author:
            return await ctx.send("❌ You cannot spar with yourself.", ephemeral=True)
        if opponent.bot:
            return await ctx.send("❌ You cannot spar with a bot.", ephemeral=True)

        # Cooldown check
        on_cd, remaining = await self._check_cooldown(ctx.author.id)
        if on_cd:
            return await ctx.send(f"⏳ You must wait **{remaining} seconds** before sparring again.", ephemeral=True)

        # Minimum rank check (Third-Rate Warrior)
        rank = await get_user_stat(self.bot.db, ctx.author.id, "rank") or "The Bound (Mortal)"
        if "Third-Rate" not in rank and "Second-Rate" not in rank and "First-Rate" not in rank and "Peak Master" not in rank:
            return await ctx.send("❌ You must be at least **Third-Rate Warrior** to spar.", ephemeral=True)

        # Prevent sparring while meditating
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send(config.MSG_ALREADY_MEDITATING, ephemeral=True)
        if hasattr(self.bot, 'is_meditating') and opponent.id in self.bot.is_meditating:
            return await ctx.send(f"❌ {opponent.display_name} is meditating and cannot spar.", ephemeral=True)

        # Prevent sparring while in combat (hunting)
        if hasattr(self.bot, 'active_combats'):
            if ctx.author.id in self.bot.active_combats:
                return await ctx.send("❌ You are already in combat! Finish your hunt first.", ephemeral=True)
            if opponent.id in self.bot.active_combats:
                return await ctx.send(f"❌ {opponent.display_name} is already in combat.", ephemeral=True)

        # Bet validation
        if bet < 0:
            return await ctx.send("❌ Bet amount cannot be negative.", ephemeral=True)
        if bet > 0:
            MIN_BET = 10
            if bet < MIN_BET:
                return await ctx.send(f"❌ Minimum bet is **{MIN_BET} Taels**.", ephemeral=True)
            author_taels = await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0
            if author_taels < bet:
                return await ctx.send(f"❌ You don't have enough Taels. You have {author_taels}, bet is {bet}.", ephemeral=True)

        # Save pre-spar stats (HP and Vitality) for both players
        pre_spar_stats = {
            ctx.author.id: {
                "hp": await get_user_stat(self.bot.db, ctx.author.id, "hp") or 100,
                "vitality": await get_user_stat(self.bot.db, ctx.author.id, "vitality") or 100,
            },
            opponent.id: {
                "hp": await get_user_stat(self.bot.db, opponent.id, "hp") or 100,
                "vitality": await get_user_stat(self.bot.db, opponent.id, "vitality") or 100,
            },
        }

        # Use real HP for the spar (based on their current stats)
        challenger_hp = pre_spar_stats[ctx.author.id]["hp"]
        opponent_hp = pre_spar_stats[opponent.id]["hp"]

        # Confirm opponent accepts
        view = discord.ui.View(timeout=60)
        accept_button = discord.ui.Button(label="Accept", style=discord.ButtonStyle.success)
        decline_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.danger)

        async def accept_callback(interaction):
            if interaction.user != opponent:
                return await interaction.response.send_message("❌ Only the opponent can accept.", ephemeral=True)
            if bet > 0:
                opponent_taels = await get_user_stat(self.bot.db, opponent.id, "taels") or 0
                if opponent_taels < bet:
                    await interaction.response.edit_message(content=f"❌ {opponent.display_name} doesn't have enough Taels to accept the bet ({bet} required).", view=None)
                    return
            await interaction.response.edit_message(content="✅ Spar accepted! Starting...", view=None)
            # Set cooldown for both players
            await self._set_cooldown(ctx.author.id)
            await self._set_cooldown(opponent.id)
            # Create the spar view
            spar_view = SparView(self.bot, ctx.author, opponent, challenger_hp, opponent_hp, bet, pre_spar_stats)
            embed = discord.Embed(
                title="⚔️ Spar Started!",
                description=f"{ctx.author.mention} vs {opponent.mention}\n{ctx.author.display_name} goes first.",
                color=format_embed_color("main")
            )
            if bet > 0:
                embed.add_field(name="💰 Bet", value=f"{bet} Taels (winner takes all)", inline=False)
            await ctx.send(embed=embed, view=spar_view)

        async def decline_callback(interaction):
            if interaction.user != opponent:
                return await interaction.response.send_message("❌ Only the opponent can decline.", ephemeral=True)
            await interaction.response.edit_message(content=f"❌ {opponent.display_name} declined the spar.", view=None)

        accept_button.callback = accept_callback
        decline_button.callback = decline_callback
        view.add_item(accept_button)
        view.add_item(decline_button)

        bet_text = f" with a bet of **{bet} Taels**" if bet > 0 else ""
        await ctx.send(f"{opponent.mention}, {ctx.author.display_name} challenges you to a spar{bet_text}! Do you accept?", view=view)

async def setup(bot):
    await bot.add_cog(PvP(bot))
    print("[DEBUG] pvp.py: Setup complete")