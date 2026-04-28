import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

# --- V2 UI BUTTON ---
class StatusView(discord.ui.View):
    def __init__(self, bot, target, get_db):
        super().__init__(timeout=30)
        self.bot = bot
        self.target = target
        self.get_db = get_db

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray)
    async def refresh_button(self, interaction: discord.Interaction):
        # Logic to recreate the embed with fresh data
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("""
            SELECT background, rank, taels, ki, vitality, hp, item_id 
            FROM users WHERE user_id=?
        """, (self.target.id,)).fetchone()
        conn.close()

        if not user:
            return await interaction.response.send_message("Data lost.", ephemeral=True)

        bg, rank, taels, ki, vit, hp, item = user
        
        # --- UPDATED DYNAMIC CAP LOGIC ---
        if "Second-Rate" in rank:
            cap = 600
            ki_goal = 600 # Placeholder for Phase 2 growth
        elif "Third-Rate" in rank:
            cap = 300
            ki_goal = 300
        else:
            cap = 100
            ki_goal = 100

        embed = discord.Embed(title=f"📜 Status: {self.target.name}", color=0x700000)
        embed.set_thumbnail(url=self.target.display_avatar.url)
        embed.add_field(name="Background", value=bg, inline=True)
        embed.add_field(name="Current Rank", value=f"**{rank}**", inline=True)
        embed.add_field(name="HP", value=f"🩸 {hp}/{cap}", inline=True)
        embed.add_field(name="Vitality", value=f"❤️ {vit}/{cap}", inline=True)
        embed.add_field(name="Ki", value=f"✨ {ki}/{ki_goal}", inline=True)
        embed.add_field(name="Taels", value=f"💰 {taels}", inline=True)
        embed.add_field(name="Innate Item", value=f"📦 {item}", inline=False)
        embed.set_footer(text="Updated instantly via Qi Resonance.")
        
        await interaction.response.edit_message(embed=embed, view=self)

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="stats", description="View your progress or another player's status.")
    @app_commands.describe(member="The player whose status you want to view")
    async def stats(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("""
            SELECT background, rank, taels, ki, vitality, hp, item_id 
            FROM users WHERE user_id=?
        """, (target.id,)).fetchone()
        conn.close()

        if not user:
            msg = "❌ You haven't started yet." if target == ctx.author else f"❌ {target.name} hasn't started."
            return await ctx.send(msg)

        bg, rank, taels, ki, vit, hp, item = user

        # --- UPDATED DYNAMIC CAP LOGIC ---
        if "Second-Rate" in rank:
            cap = 600
            ki_goal = 600
        elif "Third-Rate" in rank:
            cap = 300
            ki_goal = 300
        else:
            cap = 100
            ki_goal = 100

        embed = discord.Embed(title=f"📜 Status: {target.name}", color=0x700000)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Background", value=bg, inline=True)
        embed.add_field(name="Current Rank", value=f"**{rank}**", inline=True)
        embed.add_field(name="HP", value=f"🩸 {hp}/{cap}", inline=True)
        embed.add_field(name="Vitality", value=f"❤️ {vit}/{cap}", inline=True)
        embed.add_field(name="Ki", value=f"✨ {ki}/{ki_goal}", inline=True)
        embed.add_field(name="Taels", value=f"💰 {taels}", inline=True)
        embed.add_field(name="Innate Item", value=f"📦 {item}", inline=False)
        
        footer_text = "Focus your spirit." if target == ctx.author else f"Observing {target.name}'s foundation..."
        embed.set_footer(text=footer_text)
        
        # Only show the refresh button if looking at your own stats
        view = StatusView(self.bot, target, self.get_db) if target == ctx.author else None
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Status(bot))
