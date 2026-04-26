import discord
from discord.ext import commands
import sqlite3

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # HYBRID COMMAND: !stats / /stats
    # ==========================================
    @commands.hybrid_command(name="stats", description="Displays your current progress and status.")
    async def stats(self, ctx):
        """Displays your current progress and status."""
        conn = self.get_db()
        c = conn.cursor()
        
        # We now pull EVERY relevant column from your Phase 1 Plan
        user = c.execute("""
            SELECT background, rank, taels, ki, vitality, hp, item_id 
            FROM users WHERE user_id=?
        """, (ctx.author.id,)).fetchone()
        conn.close()

        if not user:
            return await ctx.send("❌ You have no status. Use /start to begin your struggle.")

        # Mapping the database results to variables
        bg, rank, taels, ki, vit, hp, item = user

        embed = discord.Embed(title=f"📜 Status: {ctx.author.name}", color=0x700000)
        
        # Section 1: Identity & Rank
        embed.add_field(name="Background", value=bg, inline=True)
        embed.add_field(name="Current Rank", value=f"**{rank}**", inline=True)
        
        # Section 2: Vital Statistics
        embed.add_field(name="HP", value=f"🩸 {hp}/100", inline=True)
        embed.add_field(name="Vitality", value=f"❤️ {vit}/100", inline=True)
        
        # Section 3: Progress & Wealth
        embed.add_field(name="Ki", value=f"✨ {ki}/100", inline=True)
        embed.add_field(name="Taels", value=f"💰 {taels}", inline=True)
        
        # Section 4: The Innate Item (This will show the Mutated version after breakthrough)
        embed.add_field(name="Innate Item", value=f"📦 {item}", inline=False)
        
        embed.set_footer(text="Focus your spirit. Break your chains.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
