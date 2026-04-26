import discord
from discord.ext import commands
import sqlite3

PERMANENT_GOD = 756012403291848804 
temporary_gods = set() # Stores IDs of people you promote

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin(self, user_id):
        return user_id == PERMANENT_GOD or user_id in temporary_gods

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # DIVINE DECREE (Promote/Demote)
    # ==========================================
    @commands.command()
    async def promote(self, ctx, member: discord.Member):
        """Grant temporary God Powers to a user."""
        if ctx.author.id != PERMANENT_GOD: return
        temporary_gods.add(member.id)
        await ctx.send(f"🌟 {member.mention} has been granted Divine Authority by the Creator.")

    @commands.command()
    async def demote(self, ctx, member: discord.Member):
        """Strip God Powers from a user."""
        if ctx.author.id != PERMANENT_GOD: return
        temporary_gods.discard(member.id)
        await ctx.send(f"🌑 {member.mention} has been stripped of their authority.")

    # ==========================================
    # TARGETED GOD COMMANDS
    # ==========================================
    @commands.command()
    async def setki(self, ctx, amount: int, member: discord.Member = None):
        """Set Ki for yourself or a tagged user."""
        if not self.is_admin(ctx.author.id): return
        target = member or ctx.author
        conn = self.get_db()
        conn.execute("UPDATE users SET ki = ? WHERE user_id = ?", (amount, target.id))
        conn.commit()
        conn.close()
        await ctx.send(f"🪄 Set **{target.name}'s** Ki to {amount}.")

    @commands.command()
    async def refill(self, ctx, member: discord.Member = None):
        """Refill Vitality for yourself or a tagged user."""
        if not self.is_admin(ctx.author.id): return
        target = member or ctx.author
        conn = self.get_db()
        conn.execute("UPDATE users SET vitality = 100 WHERE user_id = ?", (target.id,))
        conn.commit()
        conn.close()
        await ctx.send(f"🍷 Restored **{target.name}'s** Vitality.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
