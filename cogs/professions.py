import discord
from discord.ext import commands
from utils.db import get_bot_setting, is_user_banned
import config

print("[DEBUG] professions.py: Loading Professions cog...")

class Professions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.professions_list = ["Alchemist", "Blacksmith", "Herb Gatherer", "Formation Master", "Instructor"]
        print("[DEBUG] Professions cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_professions", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Professions"), ephemeral=True)
        return enabled

    def progress_bar(self, current, required):
        segments = 10
        ratio = max(0, min(current / required, 1))
        filled = int(ratio * segments)
        bar = "🟥" * filled + "⬛" * (segments - filled)
        percent = int(ratio * 100)
        return bar, percent

    @commands.hybrid_command(name="pchoose", description="Commit to a life-path profession")
    async def pchoose(self, ctx, profession: str = None):
        print(f"[DEBUG] professions.pchoose: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        db = self.bot.db
        user = await db.users.find_one({"user_id": ctx.author.id})

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        current_prof = user.get("profession", "None")

        if current_prof != "None":
            embed = discord.Embed(
                title="📜 Path Already Chosen",
                description=f"You are already dedicated to the path of a **{current_prof}**.",
                color=0x700000
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if profession is None or profession.title() not in self.professions_list:
            list_str = "\n".join([f"• {p}" for p in self.professions_list])
            embed = discord.Embed(
                title="⚒️ Choose Your Profession",
                description=f"Use `!pchoose <name>` to select your path:\n\n{list_str}",
                color=0x700000
            )
            return await ctx.send(embed=embed, ephemeral=True)

        chosen = profession.title()

        await db.users.update_one(
            {"user_id": ctx.author.id},
            {"$set": {"profession": chosen}}
        )

        embed = discord.Embed(
            title="✅ Profession Bound",
            description=f"You have begun your journey as a **{chosen}**.\nThis choice is permanent.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pstatus", description="Check your professional standing")
    async def pstatus(self, ctx):
        print(f"[DEBUG] professions.pstatus: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        db = self.bot.db
        user = await db.users.find_one({"user_id": ctx.author.id})

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        prof = user.get("profession", "None")
        rank = user.get("prof_rank", "Apprentice")
        xp = user.get("prof_xp", 0)
        req_xp = user.get("prof_req_xp", 1000)

        if prof == "None":
            embed = discord.Embed(
                title="Profession Required",
                description="You must choose a profession before viewing progress.\nUse `!pchoose`.",
                color=0x700000
            )
            return await ctx.send(embed=embed, ephemeral=True)

        bar, percent = self.progress_bar(xp, req_xp)

        embed = discord.Embed(
            title="📜 Professional Standing",
            color=0x700000
        )
        embed.add_field(name="Path", value=prof, inline=True)
        embed.add_field(name="Rank", value=rank, inline=True)
        embed.add_field(name="Experience", value=f"{bar} **{percent}%**\n{xp} / {req_xp} XP", inline=False)
        embed.add_field(
            name="⭐ Talent",
            value="**Professional Insight**\n✨ +10% XP Gain\n✨ +5% Success Rate",
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Professions(bot))
    print("[DEBUG] professions.py: Setup complete")