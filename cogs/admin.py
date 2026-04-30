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
    # SYNC COMMAND (Invisible to players)
    # ==========================================
    @commands.command()
    async def sync(self, ctx):
        """Forces Discord to show your bot's Slash Commands."""
        if not self.is_admin(ctx.author.id): return
        await ctx.send("📡 Syncing with the heavens...")
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Success! **{len(synced)}** commands registered to the `/` menu.")
        except Exception as e:
            await ctx.send(f"❌ Sync failed: {e}")

    # ==========================================
    # GHOST PROTOCOL: !divine
    # ==========================================
    @commands.command()
    async def divine(self, ctx):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        
        embed = discord.Embed(title="⚡ The Divine Scroll", color=0xFFD700)
        embed.description = (
            "**Admin Commands:**\n"
            "`!sync` - Register Slash Commands\n"
            "`!pulse` - Force Recovery Heartbeat\n"
            "`!promote @user` - Grant God Powers\n"
            "`!demote @user` - Strip God Powers\n"
            "`!setki <num> @user` - Set Ki levels\n"
            "`!settaels <num> @user` - Set Tael amount\n"
            "`!setmastery <num> @user` - Set Technique Mastery\n"
            "`!refill @user` - Full HP/Vit restoration\n"
            "`!reset @user` - Erase a player"
        )
        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ Open your DMs to receive the scroll.", delete_after=5)

    # ==========================================
    # DIVINE PULSE
    # ==========================================
    @commands.command()
    async def pulse(self, ctx):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        mechanics_cog = self.bot.get_cog('Mechanics')
        if mechanics_cog:
            await mechanics_cog.heartbeat()
            await ctx.send("🌀 **Divine Pulse:** Recovery triggered.", delete_after=5)

    # ==========================================
    # USER MANAGEMENT
    # ==========================================
    @commands.command()
    async def promote(self, ctx, member: discord.Member):
        if ctx.author.id != PERMANENT_GOD: return
        await ctx.message.delete()
        temporary_gods.add(member.id)
        await ctx.send(f"🌟 {member.mention} promoted to Temporary God.", delete_after=5)

    @commands.command()
    async def demote(self, ctx, member: discord.Member):
        """Removes a user from the temporary gods list."""
        if ctx.author.id != PERMANENT_GOD: return
        await ctx.message.delete()
        if member.id in temporary_gods:
            temporary_gods.remove(member.id)
            await ctx.send(f"💢 {member.mention} stripped of Divine Power.", delete_after=5)
        else:
            await ctx.send(f"❌ {member.mention} is not a God.", delete_after=5)

    @commands.command()
    async def reset(self, ctx, member: discord.Member = None):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        target = member or ctx.author
        conn = self.get_db()
        conn.execute("DELETE FROM users WHERE user_id = ?", (target.id,))
        conn.commit()
        conn.close()
        await ctx.send(f"♻️ **Divine Reset:** {target.name} erased from history.", delete_after=5)

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

    # ==========================================
    # NEW: TAEL & MASTERY CONTROL
    # ==========================================
    @commands.command()
    async def settaels(self, ctx, amount: int, member: discord.Member = None):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        target = member or ctx.author
        conn = self.get_db()
        conn.execute("UPDATE users SET taels = ? WHERE user_id = ?", (amount, target.id))
        conn.commit()
        conn.close()
        await ctx.send(f"💰 Taels set to {amount} for {target.name}.", delete_after=5)

    @commands.command()
    async def setmastery(self, ctx, amount: float, member: discord.Member = None):
        if not self.is_admin(ctx.author.id): return
        await ctx.message.delete()
        target = member or ctx.author
        conn = self.get_db()
        conn.execute("UPDATE users SET mastery = ? WHERE user_id = ?", (amount, target.id))
        conn.commit()
        conn.close()
        await ctx.send(f"📖 Mastery set to {amount}% for {target.name}.", delete_after=5)

    # ==========================================
    # REFILL: Updated for Dynamic Scaling
    # ==========================================
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

        caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 300, "Second-Rate Warrior": 600}
        max_v = caps.get(user[0], 1000)

        c.execute("UPDATE users SET vitality = ?, hp = ? WHERE user_id = ?", (max_v, max_v, target.id))
        conn.commit()
        conn.close()
        await ctx.send(f"🍷 **Divine Favor:** {target.name} restored to {max_v} Vitality.", delete_after=5)

async def setup(bot):
    await bot.add_cog(Admin(bot))
