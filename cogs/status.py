import discord
from discord.ext import commands
import sqlite3

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # COMMAND: !stats (The Mortal Status)
    # ==========================================
    @commands.command()
    async def stats(self, ctx):
        """Displays your current progress and status."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, taels, ki, vitality, item_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user:
            return await ctx.send("You have no status. Use !start to begin your struggle.")

        embed = discord.Embed(title=f"Status: {ctx.author.name}", color=0x700000)
        embed.add_field(name="Rank/Background", value=user[0], inline=True)
        embed.add_field(name="Vitality", value=f"❤️ {user[3]}/100", inline=True)
        embed.add_field(name="Taels", value=f"💰 {user[1]}", inline=True)
        embed.add_field(name="Ki", value=f"✨ {user[2]}", inline=True)
        embed.add_field(name="Innate Item", value=f"📦 {user[4]}", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))

