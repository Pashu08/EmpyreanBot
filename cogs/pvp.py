import discord
from discord.ext import commands
import random
import asyncio

class SparView(discord.ui.View):
    def __init__(self, bot, challenger, opponent, challenger_hp, opponent_hp):
        super().__init__(timeout=60)
        self.bot = bot
        self.challenger = challenger
        self.opponent = opponent
        self.challenger_hp = challenger_hp
        self.opponent_hp = opponent_hp
        self.turn = "challenger"  # challenger goes first
        self.log = "The spar begins!"

    async def update_message(self, interaction, embed, view):
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except:
            await interaction.edit_original_response(embed=embed, view=view)

    async def end_spar(self, interaction, winner, loser):
        embed = discord.Embed(title="⚔️ Spar Finished", color=0x00FF00 if winner == self.challenger else 0xFF0000)
        embed.description = f"**{winner.display_name}** defeated **{loser.display_name}**!\n{self.log}"
        for child in self.children:
            child.disabled = True
        await self.update_message(interaction, embed, self)
        self.stop()

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger)
    async def strike(self, interaction, button):
        if interaction.user not in (self.challenger, self.opponent):
            return await interaction.response.send_message("Not your fight!", ephemeral=True)
        if (self.turn == "challenger" and interaction.user != self.challenger) or (self.turn == "opponent" and interaction.user != self.opponent):
            return await interaction.response.send_message("Wait for your turn!", ephemeral=True)

        dmg = random.randint(10, 25)
        if self.turn == "challenger":
            self.opponent_hp -= dmg
            self.log = f"{self.challenger.display_name} strikes for {dmg} damage!"
            self.turn = "opponent"
        else:
            self.challenger_hp -= dmg
            self.log = f"{self.opponent.display_name} strikes for {dmg} damage!"
            self.turn = "challenger"

        embed = discord.Embed(title=f"⚔️ Spar: {self.challenger.display_name} vs {self.opponent.display_name}", color=0x700000)
        embed.add_field(name=f"{self.challenger.display_name}", value=f"HP: {max(0, self.challenger_hp)}", inline=True)
        embed.add_field(name=f"{self.opponent.display_name}", value=f"HP: {max(0, self.opponent_hp)}", inline=True)
        embed.add_field(name="Combat Log", value=self.log, inline=False)

        if self.challenger_hp <= 0:
            await self.end_spar(interaction, self.opponent, self.challenger)
        elif self.opponent_hp <= 0:
            await self.end_spar(interaction, self.challenger, self.opponent)
        else:
            await self.update_message(interaction, embed, self)

class PvP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="spar", description="Challenge another user to a friendly spar (no rewards).")
    async def spar(self, ctx, opponent: discord.Member):
        if opponent == ctx.author:
            return await ctx.send("❌ You cannot spar with yourself.", ephemeral=True)
        if opponent.bot:
            return await ctx.send("❌ You cannot spar with a bot.", ephemeral=True)

        # Confirm opponent accepts
        view = discord.ui.View()
        accept_button = discord.ui.Button(label="Accept", style=discord.ButtonStyle.success)
        decline_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.danger)

        async def accept_callback(interaction):
            if interaction.user != opponent:
                return await interaction.response.send_message("Only the opponent can accept.", ephemeral=True)
            await interaction.response.edit_message(content="Spar accepted! Starting...", view=None)
            # Both start with 100 HP
            view = SparView(self.bot, ctx.author, opponent, 100, 100)
            embed = discord.Embed(title="⚔️ Spar Started!", description=f"{ctx.author.mention} vs {opponent.mention}\n{ctx.author.display_name} goes first.", color=0x700000)
            await ctx.send(embed=embed, view=view)

        async def decline_callback(interaction):
            if interaction.user != opponent:
                return await interaction.response.send_message("Only the opponent can decline.", ephemeral=True)
            await interaction.response.edit_message(content=f"{opponent.display_name} declined the spar.", view=None)

        accept_button.callback = accept_callback
        decline_button.callback = decline_callback
        view.add_item(accept_button)
        view.add_item(decline_button)

        await ctx.send(f"{opponent.mention}, {ctx.author.display_name} challenges you to a spar! Do you accept?", view=view)

async def setup(bot):
    await bot.add_cog(PvP(bot))