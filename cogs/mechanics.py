import logging
import asyncio
import datetime

import discord
from discord.ext import commands, tasks

from utils.helpers import get_max_stats
from utils.db import get_bot_setting

log = logging.getLogger(__name__)

class Mechanics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meditating: set[int] = set()
        self.meditation_start_times: dict[int, datetime.datetime] = {}
        if not hasattr(self.bot, "is_meditating"):
            self.bot.is_meditating = set()
        self.recover_cooldowns: dict[int, datetime.datetime] = {}
        self.focus_cooldowns:   dict[int, datetime.datetime] = {}
        self.rest_cooldowns:    dict[int, datetime.datetime] = {}
        self.bot.loop.create_task(self._delayed_start())

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_mechanics", True)
        if not enabled:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Feature Disabled",
                    description="The mechanics system is currently disabled.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )
        return enabled

    async def _delayed_start(self):
        await self.bot.wait_until_ready()
        self.heartbeat.start()
        log.info("Mechanics cog ready; heartbeat started.")

    def cog_unload(self):
        self.heartbeat.cancel()

    # ------------------------------------------------------------------
    # Heartbeat (MongoDB version)
    # ------------------------------------------------------------------
    @tasks.loop(minutes=20.0)
    async def heartbeat(self):
        db = self.bot.db
        cursor = db.users.find({})
        users = await cursor.to_list(length=1000)

        dm_count = 0

        for user in users:
            u_id = user.get("user_id")
            current_hp = user.get("hp", 0)
            current_vit = user.get("vitality", 0)
            rank = user.get("rank", "The Bound (Mortal)")
            dm_enabled = user.get("heartbeat_dm", 1)

            if "Second-Rate" in rank:
                regen = 100
            elif "Third-Rate" in rank:
                regen = 50
            else:
                regen = 25

            max_stats = get_max_stats(rank)
            new_hp = min(current_hp + regen, max_stats["max_hp"])
            new_vit = min(current_vit + regen, max_stats["max_vit"])

            hp_gain = new_hp - current_hp
            vit_gain = new_vit - current_vit

            if hp_gain == 0 and vit_gain == 0:
                continue

            await db.users.update_one(
                {"user_id": u_id},
                {"$set": {"hp": new_hp, "vitality": new_vit}}
            )

            if dm_enabled:
                user_obj = self.bot.get_user(u_id)
                if user_obj:
                    try:
                        dm_count += 1
                        if dm_count % 5 == 0:
                            await asyncio.sleep(1)

                        embed = discord.Embed(
                            title="🌿 Heavenly Recovery",
                            description=(
                                f"You regain **{hp_gain} HP** and **{vit_gain} Vitality**.\n"
                                f"Current: {new_hp} HP / {new_vit} Vitality"
                            ),
                            color=0x43B581,
                        )
                        embed.set_footer(text="You can disable these DMs with /toggle_dm")
                        await user_obj.send(embed=embed)
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException as e:
                        if e.status == 429:
                            await asyncio.sleep(2)
                            log.warning(f"Heartbeat DM rate limited for user {u_id}")

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # ------------------------------------------------------------------
    # Helpers (unchanged)
    # ------------------------------------------------------------------
    @staticmethod
    def _utcnow() -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)

    def _cooldown_remaining(self, store: dict[int, datetime.datetime], user_id: int) -> int | None:
        end = store.get(user_id)
        if end is None:
            return None
        remaining = (end - self._utcnow()).total_seconds()
        return int(remaining) if remaining > 0 else None

    # ------------------------------------------------------------------
    # toggle_dm (MongoDB version)
    # ------------------------------------------------------------------
    @commands.hybrid_command(name="toggle_dm", description="Enable/disable heartbeat recovery DMs")
    async def toggle_dm(self, ctx):
        print(f"[DEBUG] mechanics.toggle_dm: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        db = self.bot.db
        user = await db.users.find_one({"user_id": ctx.author.id})

        if not user:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Not Registered",
                    description="Use `/start` first.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

        current = user.get("heartbeat_dm", 1)
        new = 0 if current else 1

        await db.users.update_one(
            {"user_id": ctx.author.id},
            {"$set": {"heartbeat_dm": new}}
        )

        await ctx.send(
            embed=discord.Embed(
                title="✅ DM Toggle",
                description=f"Heartbeat DMs **{'enabled' if new else 'disabled'}**.",
                color=0x43B581,
            ),
            ephemeral=True,
        )

    # ------------------------------------------------------------------
    # recover (MongoDB version)
    # ------------------------------------------------------------------
    @commands.hybrid_command(name="recover", description="Meditate for 60 s to restore Vitality and Ki (5 min cooldown)")
    async def recover(self, ctx):
        print(f"[DEBUG] mechanics.recover: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        user_id = ctx.author.id

        remaining = self._cooldown_remaining(self.recover_cooldowns, user_id)
        if remaining is not None:
            return await ctx.send(
                embed=discord.Embed(
                    title="⏳ Meditation Cooldown",
                    description=f"Please wait **{remaining} seconds**.",
                    color=0xF1C40F,
                ),
                ephemeral=True,
            )

        if user_id in self.meditating:
            return await ctx.send(
                embed=discord.Embed(
                    title="🧘 Already Meditating",
                    description="You are already in deep meditation.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

        self.meditating.add(user_id)
        self.meditation_start_times[user_id] = self._utcnow()
        self.bot.is_meditating.add(user_id)

        msg = await ctx.send(
            embed=discord.Embed(
                title="🧘 Meditation Begins",
                description="You enter a state of deep meditation… (60 s)",
                color=0x9B59B6,
            )
        )

        total_time = 60
        elapsed = 0
        cancelled = False

        while elapsed < total_time:
            await asyncio.sleep(10)
            elapsed += 10

            if user_id not in self.meditating:
                cancelled = True
                break

            remaining_secs = total_time - elapsed
            percent = max(0, remaining_secs / total_time) * 100
            filled = int(percent / 10)
            bar = "█" * filled + "░" * (10 - filled)
            label = f"**{remaining_secs}s** left…" if remaining_secs > 0 else "Almost there…"
            await msg.edit(
                embed=discord.Embed(
                    title="🧘 Meditating",
                    description=f"`[{bar}]` {label}",
                    color=0x9B59B6,
                )
            )

        self.meditating.discard(user_id)
        self.meditation_start_times.pop(user_id, None)
        self.bot.is_meditating.discard(user_id)

        if cancelled:
            return

        db = self.bot.db
        user = await db.users.find_one({"user_id": user_id})

        if not user:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Not Registered",
                    description="Use `/start` first.",
                    color=0xE74C3C,
                )
            )

        rank = user.get("rank", "The Bound (Mortal)")
        current_ki = user.get("ki", 0)
        current_vit = user.get("vitality", 0)
        background = user.get("background", "")

        max_stats = get_max_stats(rank)

        vit_gain = 35 if background == "Hermit" else 25
        ki_gain = 15 if background == "Hermit" else 5

        new_vit = min(max_stats["max_vit"], current_vit + vit_gain)
        new_ki = min(max_stats["ki_cap"], current_ki + ki_gain)

        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"vitality": new_vit, "ki": new_ki}}
        )

        self.recover_cooldowns[user_id] = self._utcnow() + datetime.timedelta(minutes=5)

        bonus = " *(+Hermit bonus)*" if background == "Hermit" else ""
        await msg.edit(
            embed=discord.Embed(
                title="✨ Meditation Complete",
                description=(
                    f"You regained **+{vit_gain} Vitality** and **+{ki_gain} Ki**{bonus}.\n"
                    f"Current: {new_vit} Vitality | {new_ki} Ki"
                ),
                color=0x2ECC71,
            )
        )

    # ------------------------------------------------------------------
    # cancel (unchanged)
    # ------------------------------------------------------------------
    @commands.hybrid_command(name="cancel", description="Cancel active meditation")
    async def cancel_meditation(self, ctx):
        print(f"[DEBUG] mechanics.cancel_meditation: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        user_id = ctx.author.id
        if user_id in self.meditating:
            if user_id in self.meditation_start_times:
                elapsed = (self._utcnow() - self.meditation_start_times[user_id]).total_seconds()
                if elapsed < 30:
                    self.recover_cooldowns[user_id] = self._utcnow() + datetime.timedelta(minutes=2)
                    await ctx.send(
                        embed=discord.Embed(
                            title="⚠️ Early Cancellation Penalty",
                            description="Cancelling within 30 seconds applies a 2-minute cooldown!",
                            color=0xF1C40F,
                        ),
                        ephemeral=True,
                    )

            self.meditating.discard(user_id)
            self.meditation_start_times.pop(user_id, None)
            self.bot.is_meditating.discard(user_id)
            await ctx.send(
                embed=discord.Embed(
                    title="🧘 Meditation Cancelled",
                    description="You snap out of your meditation early.",
                    color=0xF1C40F,
                ),
                ephemeral=True,
            )
        else:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ Not Meditating",
                    description="You are not currently meditating.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

    # ------------------------------------------------------------------
    # meditate_status (MongoDB version)
    # ------------------------------------------------------------------
    @commands.hybrid_command(name="meditate", description="Check next heartbeat and your stats")
    async def meditate_status(self, ctx):
        print(f"[DEBUG] mechanics.meditate_status: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        next_it = self.heartbeat.next_iteration
        if not next_it:
            return await ctx.send(
                embed=discord.Embed(
                    title="⏳ Heartbeat Not Ready",
                    description="Please wait a moment.",
                    color=0xF1C40F,
                ),
                ephemeral=True,
            )

        now = self._utcnow()
        left = next_it - now
        minutes = int(left.total_seconds() // 60)
        seconds = int(left.total_seconds() % 60)

        db = self.bot.db
        user = await db.users.find_one({"user_id": ctx.author.id})

        if not user:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Not Registered",
                    description="Use `/start` first.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

        rank = user.get("rank", "The Bound (Mortal)")
        ki = user.get("ki", 0)
        vit = user.get("vitality", 0)
        hp = user.get("hp", 0)

        max_stats = get_max_stats(rank)
        ki_cap = max_stats["ki_cap"]
        vit_cap = max_stats["max_vit"]
        hp_cap = max_stats["max_hp"]

        from utils.constants import HEARTBEAT_REGEN
        regen = HEARTBEAT_REGEN.get(rank, 25)

        ki_progress = int((ki / ki_cap) * 100) if ki_cap else 0
        bar_filled = int(ki_progress / 10)
        ki_bar = "█" * bar_filled + "░" * (10 - bar_filled)

        recover_cd_text = ""
        rem = self._cooldown_remaining(self.recover_cooldowns, ctx.author.id)
        if rem is not None:
            recover_cd_text = f"\n⏳ `/recover` ready in **{rem}s**"

        embed = discord.Embed(
            title="🧘 Meditation Status",
            description=f"The heavens will breathe again in **{minutes}m {seconds}s**.",
            color=0x9B59B6,
        )
        embed.add_field(
            name="🌿 Next Recovery",
            value=f"Restores **{regen} HP** and **{regen} Vitality**.",
            inline=False,
        )
        embed.add_field(
            name="📊 Your Progress",
            value=(
                f"🩸 **HP:** {hp}/{hp_cap}\n"
                f"❤️ **Vitality:** {vit}/{vit_cap}\n"
                f"✨ **Ki:** {ki}/{ki_cap} (`{ki_bar}` {ki_progress}%)"
            ),
            inline=False,
        )
        if recover_cd_text:
            embed.add_field(name="⏳ Cooldowns", value=recover_cd_text, inline=False)
        embed.set_footer(text="Use /toggle_dm to enable/disable heartbeat DMs.")
        await ctx.send(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # focus (MongoDB version)
    # ------------------------------------------------------------------
    @commands.hybrid_command(name="focus", description="Convert 10 Vitality into 5 Ki (5 min cooldown)")
    async def focus(self, ctx):
        print(f"[DEBUG] mechanics.focus: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        user_id = ctx.author.id

        remaining = self._cooldown_remaining(self.focus_cooldowns, user_id)
        if remaining is not None:
            return await ctx.send(
                embed=discord.Embed(
                    title="⏳ Focus Cooldown",
                    description=f"Wait **{remaining} seconds**.",
                    color=0xF1C40F,
                ),
                ephemeral=True,
            )

        db = self.bot.db
        user = await db.users.find_one({"user_id": user_id})

        if not user:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Not Registered",
                    description="Use `/start` first.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

        vit = user.get("vitality", 0)
        ki = user.get("ki", 0)
        rank = user.get("rank", "The Bound (Mortal)")
        max_stats = get_max_stats(rank)

        if vit < 10:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Low Vitality",
                    description=f"You need 10 Vitality (you have {vit}).",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

        new_vit = vit - 10
        new_ki = min(max_stats["ki_cap"], ki + 5)

        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"vitality": new_vit, "ki": new_ki}}
        )

        self.focus_cooldowns[user_id] = self._utcnow() + datetime.timedelta(minutes=5)

        await ctx.send(
            embed=discord.Embed(
                title="🌀 Focused Energy",
                description=(
                    f"You converted **10 Vitality** into **5 Ki**.\n"
                    f"Vitality: {new_vit}/{max_stats['max_vit']}\n"
                    f"Ki: {new_ki}/{max_stats['ki_cap']}"
                ),
                color=0x3498DB,
            )
        )

    # ------------------------------------------------------------------
    # rest (MongoDB version)
    # ------------------------------------------------------------------
    @commands.hybrid_command(name="rest", description="Instantly restore 10 HP and 10 Vitality (1 hour cooldown)")
    async def rest(self, ctx):
        print(f"[DEBUG] mechanics.rest: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        user_id = ctx.author.id

        remaining = self._cooldown_remaining(self.rest_cooldowns, user_id)
        if remaining is not None:
            minutes_left = remaining // 60
            seconds_left = remaining % 60
            return await ctx.send(
                embed=discord.Embed(
                    title="⏳ Rest Cooldown",
                    description=f"Next rest in **{minutes_left}m {seconds_left}s**.",
                    color=0xF1C40F,
                ),
                ephemeral=True,
            )

        db = self.bot.db
        user = await db.users.find_one({"user_id": user_id})

        if not user:
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Not Registered",
                    description="Use `/start` first.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )

        hp = user.get("hp", 0)
        vit = user.get("vitality", 0)
        rank = user.get("rank", "The Bound (Mortal)")
        max_stats = get_max_stats(rank)
        new_hp = min(max_stats["max_hp"], hp + 10)
        new_vit = min(max_stats["max_vit"], vit + 10)

        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"hp": new_hp, "vitality": new_vit}}
        )

        self.rest_cooldowns[user_id] = self._utcnow() + datetime.timedelta(hours=1)

        await ctx.send(
            embed=discord.Embed(
                title="🛌 Rest Taken",
                description=(
                    f"You regain **10 HP** and **10 Vitality**.\n"
                    f"HP: {new_hp}/{max_stats['max_hp']} | "
                    f"Vitality: {new_vit}/{max_stats['max_vit']}"
                ),
                color=0x2ECC71,
            )
        )

async def setup(bot):
    await bot.add_cog(Mechanics(bot))