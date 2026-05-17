import discord
from discord.ext import commands
import datetime
from utils.db import fetch_user, get_bot_setting, is_user_banned
from utils.helpers import get_max_stats, calculate_stage_from_ki, has_meridian_damage, format_embed_color
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
        """Check if status command is enabled (toggle_status)."""
        enabled = await get_bot_setting(self.bot.db, "toggle_status", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Status"), ephemeral=True)
        return enabled

    @commands.hybrid_command(name="stats", aliases=["st"], description="View your core cultivation stats.")
    async def stats(self, ctx, member: discord.Member = None):
        print(f"[DEBUG] status.stats: Called by {ctx.author.id}")

        # Feature toggle
        if not await self._is_feature_enabled(ctx):
            return

        # Banned check
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        target = member or ctx.author
        db = self.bot.db

        user_data = await fetch_user(db, target.id)
        if not user_data:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        # Process AFK gains (updates db and returns new data)
        now = datetime.datetime.now()
        last_refresh = user_data.get('last_refresh')
        if last_refresh:
            try:
                last_dt = datetime.datetime.fromisoformat(last_refresh)
                hours_passed = (now - last_dt).total_seconds() / 3600
                if hours_passed > 0:
                    # Simplified AFK gain: only Ki and mastery (no HP/Vit auto-regain here – handled by heartbeat)
                    ki_rate = 150  # base, but could be read from constants
                    ki_gain = int(ki_rate * hours_passed)
                    new_ki = min(user_data.get('ki', 0) + ki_gain, get_max_stats(user_data['rank'])['ki_cap'])
                    await db.execute("UPDATE users SET ki = ?, last_refresh = ? WHERE user_id = ?",
                                     (new_ki, now.isoformat(), target.id))
                    await db.commit()
                    user_data['ki'] = new_ki
                    user_data['last_refresh'] = now.isoformat()
            except:
                pass

        rank = user_data['rank']
        stage = calculate_stage_from_ki(user_data.get('ki', 0), get_max_stats(rank)['ki_cap'])
        bg = user_data.get('background', 'Unknown')
        hp = user_data.get('hp', 0)
        vitality = user_data.get('vitality', 0)
        meridian_damage = user_data.get('meridian_damage')
        damaged, minutes = has_meridian_damage(meridian_damage)
        meridian_status = f"⚠️ Damaged ({minutes}m left)" if damaged else "✅ Healthy"

        max_stats = get_max_stats(rank)
        ki = user_data.get('ki', 0)
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
            name="Vital Statistics",
            value=f"🩸 **HP:** {hp}/{max_stats['max_hp']}\n❤️ **Vit:** {vitality}/{max_stats['max_vit']}\n🧠 **Meridians:** {meridian_status}",
            inline=True
        )
        embed.add_field(
            name="Cultivation",
            value=f"✨ **Ki:** {ki}/{ki_cap}\n`{ki_bar}`\n📖 **Mastery:** {mastery:.1f}%\n`{mastery_bar}`\n⚔️ **Combat Mastery:** {combat_mastery}",
            inline=True
        )

        embed.set_footer(text="Use `!profile` for detailed character sheet.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
    print("[DEBUG] status.py: Setup complete")