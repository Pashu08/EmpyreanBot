import discord
from discord.ext import commands
import datetime
from utils.db import fetch_user, get_bot_setting, is_user_banned, update_user_stat
from utils.helpers import get_max_stats, calculate_stage_from_ki, has_meridian_damage, format_embed_color
from utils.constants import AFK_KI_PER_HOUR, AFK_MASTERY_PER_HOUR
import config

print("[DEBUG] status.py: Loading Status cog...")

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Status cog initialized")

    def progress_bar(self, current, total, length=10):
        """Return a text progress bar."""
        if total <= 0:
            return "⬜" * length
        ratio = max(0, min(current / total, 1))
        filled = int(ratio * length)
        return "🟦" * filled + "⬜" * (length - filled)

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_status", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Status"), ephemeral=True)
        return enabled

    async def _process_afk_gains(self, user_id, user_data):
        """
        Calculate and apply AFK gains.
        Returns (updated_user_data, gains_dict, hours_passed)
        """
        now = datetime.datetime.now()
        last_refresh = user_data.get('last_refresh')
        gains = {"ki": 0, "mastery": 0.0}

        if not last_refresh:
            return user_data, gains, 0

        try:
            last_dt = datetime.datetime.fromisoformat(last_refresh)
            hours_passed = (now - last_dt).total_seconds() / 3600
            if hours_passed <= 0:
                return user_data, gains, 0

            rank = user_data.get('rank', 'The Bound (Mortal)')
            profession = user_data.get('profession')
            background = user_data.get('background')

            # Ki gains from AFK using constants
            ki_rate = AFK_KI_PER_HOUR.get(rank, 150)
            ki_gain = int(ki_rate * hours_passed)
            gains["ki"] = ki_gain

            # Mastery gains from AFK
            mastery_multiplier = 1.15 if profession == "Instructor" else 1.0
            mastery_gain = AFK_MASTERY_PER_HOUR * hours_passed * mastery_multiplier
            gains["mastery"] = mastery_gain

            # Apply gains
            max_stats = get_max_stats(rank)
            new_ki = min(user_data.get('ki', 0) + ki_gain, max_stats['ki_cap'])
            new_mastery = min(100.0, user_data.get('mastery', 0.0) + mastery_gain)

            # Update stage based on new Ki
            new_stage = calculate_stage_from_ki(new_ki, max_stats['ki_cap'])

            # Update database using MongoDB
            await self.bot.db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "ki": new_ki,
                    "mastery": round(new_mastery, 2),
                    "stage": new_stage,
                    "last_refresh": now.isoformat()
                }}
            )

            # Update user_data dict
            user_data['ki'] = new_ki
            user_data['mastery'] = new_mastery
            user_data['stage'] = new_stage
            user_data['last_refresh'] = now.isoformat()

            print(f"[DEBUG] status._process_afk_gains: User {user_id} - {hours_passed:.1f}h away, gained +{ki_gain} Ki, +{mastery_gain:.1f}% Mastery")
            return user_data, gains, hours_passed

        except Exception as e:
            print(f"[DEBUG] status._process_afk_gains: Error for user {user_id}: {e}")
            return user_data, gains, 0

    @commands.hybrid_command(name="afk", aliases=["away"], description="Check your AFK gains.")
    async def afk(self, ctx):
        """Display AFK gains without showing full stats."""
        print(f"[DEBUG] status.afk: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        user_data = await fetch_user(db, user_id)
        if not user_data:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        # Process AFK gains
        updated_data, gains, hours_passed = await self._process_afk_gains(user_id, user_data)

        if hours_passed <= 0:
            embed = discord.Embed(
                title="🧘 AFK Status",
                description="You have no AFK gains to claim. Try using `!observe` or `!work` to start your journey!",
                color=format_embed_color("main")
            )
        else:
            # Format time
            hours = int(hours_passed)
            minutes = int((hours_passed - hours) * 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

            embed = discord.Embed(
                title="🌙 Welcome Back!",
                description=f"You were away for **{time_str}**.\n\n"
                           f"✨ **Ki Gained:** +{gains['ki']}\n"
                           f"📖 **Mastery Gained:** +{gains['mastery']:.1f}%",
                color=format_embed_color("teal")
            )
            embed.set_footer(text="Use `!stats` to see your full progress.")

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="stats", aliases=["st"], description="View your core cultivation stats.")
    async def stats(self, ctx, member: discord.Member = None):
        print(f"[DEBUG] status.stats: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        target = member or ctx.author
        db = self.bot.db

        user_data = await fetch_user(db, target.id)
        if not user_data:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        # Process AFK gains
        user_data, _, _ = await self._process_afk_gains(target.id, user_data)

        rank = user_data.get('rank', 'The Bound (Mortal)')
        max_stats = get_max_stats(rank)

        # Calculate stage based on current Ki
        ki = user_data.get('ki', 0)
        stage = calculate_stage_from_ki(ki, max_stats['ki_cap'])

        bg = user_data.get('background', 'Unknown')
        hp = user_data.get('hp', 0)
        vitality = user_data.get('vitality', 0)
        taels = user_data.get('taels', 0)
        meridian_damage = user_data.get('meridian_damage')
        damaged, minutes = has_meridian_damage(meridian_damage)
        meridian_status = f"⚠️ Damaged ({minutes}m left)" if damaged else "✅ Healthy"

        ki_cap = max_stats['ki_cap']
        mastery = user_data.get('mastery', 0.0)
        combat_mastery = user_data.get('combat_mastery', 0)

        # Progress bars
        ki_bar = self.progress_bar(ki, ki_cap)
        mastery_bar = self.progress_bar(mastery, 100)

        embed = discord.Embed(
            title=f"📜 Status: {target.name}",
            color=format_embed_color("main")
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        bg_emoji = "🌿" if bg == "Hermit" else "⚒️" if bg == "Laborer" else "🌑"
        embed.add_field(
            name="Identity",
            value=f"**Realm:** {rank} ({stage})\n**Path:** {bg_emoji} {bg}",
            inline=False
        )
        embed.add_field(
            name="💰 Wealth",
            value=f"{taels} Taels",
            inline=True
        )
        embed.add_field(
            name="Vital Statistics",
            value=f"🩸 **HP:** {hp}/{max_stats['max_hp']}\n❤️ **Vit:** {vitality}/{max_stats['max_vit']}\n🧠 **Meridians:** {meridian_status}",
            inline=True
        )
        embed.add_field(
            name="Cultivation",
            value=f"✨ **Ki:** {ki}/{ki_cap}\n`{ki_bar}`\n📖 **Mastery:** {mastery:.1f}%\n`{mastery_bar}`\n⚔️ **Combat Mastery:** {combat_mastery}",
            inline=True
        )

        embed.set_footer(text="Use `!profile` for detailed character sheet. Use `!afk` to check AFK gains.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
    print("[DEBUG] status.py: Setup complete")