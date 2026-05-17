import discord
from discord.ext import commands
import datetime
from utils.db import fetch_user, get_bot_setting, is_user_banned, get_inventory
from utils.helpers import format_embed_color, get_max_stats
from utils.constants import BACKGROUNDS, TECHNIQUES
import config

print("[DEBUG] profile.py: Loading Profile cog...")

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Profile cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_profile", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Profile"), ephemeral=True)
        return enabled

    def _get_background_perk(self, bg_name):
        """Return a short description of the background's perk."""
        bg = BACKGROUNDS.get(bg_name, {})
        return bg.get("perk", "No special perk.")

    async def _get_daily_bonus_status(self, user_id):
        """Return (work_available, observe_available, reset_timestamp_str)."""
        now = datetime.datetime.now()
        today = now.date().isoformat()
        work_date = await self.bot.db.execute("SELECT daily_work_date FROM users WHERE user_id=?", (user_id,))
        work_row = await work_date.fetchone()
        work_available = work_row is None or work_row[0] != today

        observe_date = await self.bot.db.execute("SELECT daily_observe_date FROM users WHERE user_id=?", (user_id,))
        observe_row = await observe_date.fetchone()
        observe_available = observe_row is None or observe_row[0] != today

        # Calculate next reset time (midnight UTC? Or local? We'll use midnight UTC for simplicity)
        next_reset = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)
        reset_delta = next_reset - now
        hours = int(reset_delta.total_seconds() // 3600)
        minutes = int((reset_delta.total_seconds() % 3600) // 60)
        reset_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        return work_available, observe_available, reset_str

    async def _get_milestone_progress(self, user_id, technique):
        """Return (reached_count, total_milestones, milestone_list)."""
        if technique == "None":
            return 0, 0, []
        flags = await self.bot.db.execute("SELECT mastery_flags FROM users WHERE user_id=?", (user_id,))
        row = await flags.fetchone()
        flags_str = row[0] if row else ""
        # format: "Flowing Cloud Steps:25,50" etc.
        reached = []
        if flags_str:
            for part in flags_str.split(","):
                if part.startswith(f"{technique}:"):
                    milestone = int(part.split(":")[1])
                    reached.append(milestone)
        total = [25, 50, 75, 100]
        return len(reached), len(total), reached

    async def _get_hidden_technique_status(self, user_id, technique):
        """If technique mastered to 100%, return hidden technique name, else None."""
        if technique == "None":
            return None
        flags = await self.bot.db.execute("SELECT mastery_flags FROM users WHERE user_id=?", (user_id,))
        row = await flags.fetchone()
        flags_str = row[0] if row else ""
        if f"{technique}:100" in flags_str.split(","):
            # Map technique to hidden technique (from actions.py logic)
            hidden_map = {
                "Flowing Cloud Steps": "Flowing Cloud Shadow Step",
                "Swift Wind Kick": "Swift Hurricane Kick",
                "Golden Bell Shield": "Indestructible Diamond Body",
                "Vajra Guard Mantra": "Vajra Body Rebirth",
            }
            return hidden_map.get(technique, "Unknown hidden technique")
        return None

    @commands.hybrid_command(name="profile", aliases=["prof"], description="View detailed character sheet.")
    async def profile(self, ctx, member: discord.Member = None):
        print(f"[DEBUG] profile.profile: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        target = member or ctx.author
        db = self.bot.db

        user_data = await fetch_user(db, target.id)
        if not user_data:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        bg = user_data.get('background', 'Unknown')
        perk = self._get_background_perk(bg)

        # Daily bonus status
        work_avail, observe_avail, reset_str = await self._get_daily_bonus_status(target.id)
        daily_line = f"Work: {'✅' if work_avail else '❌'} | Observe: {'✅' if observe_avail else '❌'} (Reset in {reset_str})"

        # Mastery milestone progress
        tech = user_data.get('active_tech', 'None')
        reached, total, _ = await self._get_milestone_progress(target.id, tech)
        milestone_line = f"{tech}: {reached}/{total} milestones" if tech != "None" else "No technique selected"

        # Hidden technique
        hidden = await self._get_hidden_technique_status(target.id, tech)
        hidden_line = f"**{hidden}**" if hidden else "None yet. Reach 100% mastery to unlock."

        # Inventory unique count
        inv = await get_inventory(db, target.id)
        inv_count = len(inv)

        # Faction placeholder
        factions = "Orthodox: 0 | Unorthodox: 0 | Demonic Cult: 0 (coming soon)"

        embed = discord.Embed(
            title=f"📜 Profile: {target.name}",
            color=format_embed_color("teal")
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="Background", value=f"**{bg}**\n{perk}", inline=False)
        embed.add_field(name="Daily Bonuses", value=daily_line, inline=False)
        embed.add_field(name="Mastery Milestones", value=milestone_line, inline=False)
        embed.add_field(name="Hidden Technique", value=hidden_line, inline=False)
        embed.add_field(name="Inventory", value=f"{inv_count} unique items", inline=True)
        embed.add_field(name="Faction Standings", value=factions, inline=False)

        embed.set_footer(text="Use `!stats` for core cultivation stats.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Profile(bot))
    print("[DEBUG] profile.py: Setup complete")