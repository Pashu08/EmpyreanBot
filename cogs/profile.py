import discord
from discord.ext import commands
import datetime
from utils.db import get_bot_setting, is_user_banned
from utils.helpers import format_embed_color
from utils.constants import BACKGROUNDS
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

    def _get_background_item(self, bg_name):
        """Return the starting item for a background."""
        bg = BACKGROUNDS.get(bg_name, {})
        return bg.get("item", "Unknown item")

    async def _get_daily_bonus_status(self, user_id, user_data):
        """Return (work_available, observe_available, reset_timestamp_str) using pre-fetched data."""
        print(f"[DEBUG] profile._get_daily_bonus_status: user_id={user_id}")
        now = datetime.datetime.now()
        today = now.date().isoformat()

        work_date = user_data.get('daily_work_date')
        observe_date = user_data.get('daily_observe_date')

        work_available = work_date is None or work_date != today
        observe_available = observe_date is None or observe_date != today

        # Calculate next reset time (midnight UTC)
        next_reset = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)
        reset_delta = next_reset - now
        hours = int(reset_delta.total_seconds() // 3600)
        minutes = int((reset_delta.total_seconds() % 3600) // 60)
        reset_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        return work_available, observe_available, reset_str

    async def _get_milestone_progress(self, technique, mastery_flags):
        """Return (reached_count, total_milestones) using pre-fetched data."""
        print(f"[DEBUG] profile._get_milestone_progress: technique={technique}")
        if technique == "None":
            return 0, 0

        reached = []
        if mastery_flags:
            try:
                for part in mastery_flags.split(","):
                    if part.startswith(f"{technique}:"):
                        milestone = int(part.split(":")[1])
                        reached.append(milestone)
            except (ValueError, IndexError):
                print(f"[DEBUG] profile._get_milestone_progress: Error parsing mastery_flags for {technique}")

        total_milestones = 4  # 25, 50, 75, 100
        return len(reached), total_milestones

    async def _get_hidden_technique_status(self, technique, mastery_flags):
        """Return hidden technique name or None if not mastered."""
        print(f"[DEBUG] profile._get_hidden_technique_status: technique={technique}")
        if technique == "None":
            return None

        if mastery_flags and f"{technique}:100" in mastery_flags.split(","):
            hidden_map = {
                "Flowing Cloud Steps": "Flowing Cloud Shadow Step",
                "Swift Wind Kick": "Swift Hurricane Kick",
                "Golden Bell Shield": "Indestructible Diamond Body",
                "Vajra Guard Mantra": "Vajra Body Rebirth",
            }
            return hidden_map.get(technique, "Unknown hidden technique")
        return None

    async def _get_inventory_summary(self, user_id):
        """Return (total_quantity, unique_count)."""
        print(f"[DEBUG] profile._get_inventory_summary: user_id={user_id}")
        db = self.bot.db
        total_qty = 0
        unique_count = 0
        try:
            cursor = db.inventory.find({"user_id": user_id})
            items = await cursor.to_list(length=100)
            for item in items:
                total_qty += item.get("quantity", 0)
                unique_count += 1
        except Exception as e:
            print(f"[DEBUG] profile._get_inventory_summary: Error - {e}")
        return total_qty, unique_count

    @commands.hybrid_command(name="profile", aliases=["prof"], description="View detailed character sheet.")
    async def profile(self, ctx, member: discord.Member = None):
        print(f"[DEBUG] profile.profile: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        target = member or ctx.author
        db = self.bot.db

        # Single query to fetch all user data using MongoDB
        user = await db.users.find_one({"user_id": target.id})
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        bg = user.get("background", "Unknown")
        taels = user.get("taels", 0)
        active_tech = user.get("active_tech", "None")
        profession = user.get("profession", "None")
        work_date = user.get("daily_work_date")
        observe_date = user.get("daily_observe_date")
        mastery_flags = user.get("mastery_flags")

        # Fetch inventory summary
        total_items, unique_items = await self._get_inventory_summary(target.id)

        # Get background perk and item
        perk = self._get_background_perk(bg)
        bg_item = self._get_background_item(bg)

        # Daily bonus status
        user_data = {
            'daily_work_date': work_date,
            'daily_observe_date': observe_date
        }
        work_avail, observe_avail, reset_str = await self._get_daily_bonus_status(target.id, user_data)
        daily_line = f"Work: {'✅' if work_avail else '❌'} | Observe: {'✅' if observe_avail else '❌'} (Reset in {reset_str})"

        # Mastery milestone progress
        reached, total = await self._get_milestone_progress(active_tech, mastery_flags)
        if active_tech != "None":
            milestone_line = f"{active_tech}: {reached}/{total} milestones"
        else:
            milestone_line = "No technique selected"

        # Hidden technique (mysterious hint, no spoiler)
        hidden = await self._get_hidden_technique_status(active_tech, mastery_flags)
        if hidden:
            hidden_line = f"**{hidden}** (discovered!)"
        elif active_tech != "None" and reached >= 3:
            hidden_line = "*You feel a deeper power within this technique...*"
        elif active_tech != "None":
            hidden_line = "*The true depth of this technique remains hidden...*"
        else:
            hidden_line = "*No technique selected.*"

        # Profession display
        profession_line = profession if profession and profession != "None" else "None"

        # Faction placeholder
        factions = "Orthodox: 0 | Unorthodox: 0 | Demonic Cult: 0 (coming soon)"

        # Build embed
        embed = discord.Embed(
            title=f"📜 Profile: {target.name}",
            color=format_embed_color("teal")
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="💰 Wealth", value=f"{taels} Taels", inline=True)
        embed.add_field(name="Background", value=f"**{bg}**\n{perk}", inline=False)
        embed.add_field(name="Background Item", value=bg_item, inline=True)
        embed.add_field(name="Profession", value=profession_line, inline=True)
        embed.add_field(name="Daily Bonuses", value=daily_line, inline=False)
        embed.add_field(name="Mastery Milestones", value=milestone_line, inline=False)
        embed.add_field(name="Hidden Technique", value=hidden_line, inline=False)
        embed.add_field(name="Inventory", value=f"{total_items} items ({unique_items} types)", inline=True)
        embed.add_field(name="Faction Standings", value=factions, inline=False)

        embed.set_footer(text="Use `!stats` for core cultivation stats.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Profile(bot))
    print("[DEBUG] profile.py: Setup complete")