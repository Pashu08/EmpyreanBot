import discord
from discord.ext import commands
import sqlite3

# This is your unique Soul Signature
CREATOR_ID = 756012403291848804 

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # CREATOR COMMAND: !setki (Instantly set Ki)
    # ==========================================
    @commands.command()
    async def setki(self, ctx, amount: int):
        """Dev Only: Set your Ki to any amount."""
        if ctx.author.id != CREATOR_ID:
            return await ctx.send("❌ Only the Creator can use God-tier commands.")
            
        conn = self.get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET ki = ? WHERE user_id = ?", (amount, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(f"🧙‍♂️ **Creator Power:** Your Ki has been set to **{amount}**.")

    # ==========================================
    # CREATOR COMMAND: !refill (Instant Vitality)
    # ==========================================
    @commands.command()
    async def refill(self, ctx):
        """Dev Only: Instant 100 Vitality."""
        if ctx.author.id != CREATOR_ID:
            return await ctx.send("❌ Only the Creator can use God-tier commands.")

        conn = self.get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET vitality = 100 WHERE user_id = ?", (ctx.author.id,))
        conn.commit()
        conn.close()
        await ctx.send("🔋 **Creator Power:** Your Vitality is fully restored.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
