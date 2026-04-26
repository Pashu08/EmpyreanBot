import discord
from discord.ext import commands
import sqlite3
import asyncio

PERMANENT_GOD = 756012403291848804 
temporary_gods = set() 

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin(self, user_id):
        return user_id == PERMANENT_GOD or user_id in temporary_gods

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # GHOST PROTOCOL: !divine (DM Command List)
    # ==========================================
    @commands.command()
    async def divine(self, ctx):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        
        embed = discord.Embed(title="⚡ The Divine Scroll", color=0xFFD700)
        embed.description = (
            "**Control the World from the Shadows:**\n\n"
            "`!promote @user` - Grant God Powers\n"
            "`!demote @user` - Strip God Powers\n"
            "`!setki <num> @user` - Set Ki levels\n"
            "`!refill @user` - Restore Vitality (Auto-detects Rank)\n"
            "`!reset @user` - Wipe a user's existence\n"
            "`!pulse` - Force the global recovery heartbeat\n\n"
            "*Your commands in the server will be auto-deleted.*"
        )
        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ Open your DMs.", delete_after=5)

    # ==========================================
    # NEW: !pulse (Trigger Recovery)
    # ==========================================
    @commands.command()
    async def pulse(self, ctx):
        """Forces the heartbeat in mechanics.py to run immediately."""
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        
        # This tells the mechanics cog to run its heartbeat logic right now
        mechanics_cog = self.bot.get_cog('Mechanics')
        if mechanics_cog:
            await mechanics_cog.heartbeat()
            await ctx.send("🌀 **Divine Pulse:** The world's energy has shifted (Recovery Triggered).", delete_after=5)
        else:
            await ctx.send("❌ Mechanics system not found.", delete_after=5)

    # ==========================================
    # DIVINE DECREE (Existing Ghost Commands)
    # ==========================================
    @commands.command()
    async def promote(self, ctx, member: discord.Member):
        if ctx.author.id != PERMANENT_GOD: return
        await ctx.message.delete()
        temporary_gods.add(member.id)
        await ctx.send(f"🌟 {member.mention} has been granted Divine Authority.", delete_after=5)

    @commands.command()
    async def demote(self, ctx, member: discord.Member):
        if ctx.author.id != PERMANENT_GOD: return
        await ctx.message.delete()
        temporary_gods.discard(member.id)
        await ctx.send(f"🌑 {member.mention} has been stripped of authority.", delete_after=5)

    @commands.command()
    async def reset(self, ctx, member: discord.Member = None):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        target = member or ctx.author
        conn = self.get_db()
        conn.execute("DELETE FROM users WHERE user_id = ?", (target.id,))
        conn.commit()
        conn.close()
        await ctx.send(f"♻️ **Divine Reset:** {target.name} erased.", delete_after=5)

    @commands.command()
    async def setki(self, ctx, amount: int, member: discord.Member = None):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        target = member or ctx.author
        conn = self.get_db()
        conn.execute("UPDATE users SET ki = ? WHERE user_id = ?", (amount, target.id))
        conn.commit()
        conn.close()
        await ctx.send(f"🪄 Ki set to {amount} for {target.name}.", delete_after=5)

    @commands.command()
    async def refill(self, ctx, member: discord.Member = None):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        target = member or ctx.author
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT rank FROM users WHERE user_id = ?", (target.id,)).fetchone()
        if not user:
            conn.close()
            return
        max_v = 300 if "Third-Rate" in user[0] else 100
        c.execute("UPDATE users SET vitality = ? WHERE user_id = ?", (max_v, target.id))
        conn.commit()
        conn.close()
        await ctx.send(f"🍷 **Divine Favor:** {target.name} restored to {max_v}.", delete_after=5)

async def setup(bot):
    await bot.add_cog(Admin(bot))
