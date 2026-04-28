import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Professions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.professions_list = ["Alchemist", "Blacksmith", "Herb Gatherer", "Formation Master", "Instructor"]

    def get_db(self):
        return sqlite3.connect('murim.db')

    def progress_bar(self, current, required):
        segments = 10
        ratio = max(0, min(current / required, 1))
        filled = int(ratio * segments)
        # Fixed the encoding for clean Discord display
        bar = "🟥" * filled + "⬛" * (segments - filled)
        percent = int(ratio * 100)
        return bar, percent

    @commands.hybrid_command(name="pchoose", description="Commit to a life-path profession")
    async def pchoose(self, ctx, profession: str = None):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT profession FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.")

        if user[0] != "None":
            embed = discord.Embed(title="📜 Path Already Chosen", description=f"You are already dedicated to the path of a **{user[0]}**.", color=0x700000)
            return await ctx.send(embed=embed)

        if profession is None or profession.title() not in self.professions_list:
            list_str = "\n".join([f"• {p}" for p in self.professions_list])
            embed = discord.Embed(title="⚒️ Choose Your Profession", description=f"Use `/pchoose <name>` to select your path:\n\n{list_str}", color=0x700000)
            return await ctx.send(embed=embed)

        chosen = profession.title()
        c.execute("UPDATE users SET profession=? WHERE user_id=?", (chosen, ctx.author.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="✅ Profession Bound", description=f"You have begun your journey as a **{chosen}**.\nThis choice is permanent.", color=0x00FF00)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pstatus", description="Check your professional standing")
    async def pstatus(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT profession, prof_rank, prof_xp, prof_req_xp FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user or user[0] == "None":
            embed = discord.Embed(title="Profession Required", description="You must choose a profession before viewing progress.\nUse `/pchoose`.", color=0x700000)
            return await ctx.send(embed=embed)

        prof, rank, xp, req_xp = user
        bar, percent = self.progress_bar(xp, req_xp)

        embed = discord.Embed(title="📜 Professional Standing", color=0x700000)
        embed.add_field(name="Path", value=prof, inline=True)
        embed.add_field(name="Rank", value=rank, inline=True)
        embed.add_field(name="Experience", value=f"{bar} **{percent}%**\n{xp} / {req_xp} XP", inline=False)
        
        # Talent logic remains as a placeholder as per the original plan
        embed.add_field(name="⭐ Talent", value="**Professional Insight**\n✨ +10% XP Gain\n✨ +5% Success Rate", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Professions(bot))
