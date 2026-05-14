import discord
from discord.ext import commands, tasks
import asyncio
import datetime
from utils.helpers import get_max_stats

class Mechanics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meditating = set()
        self.cooldowns = {}          # for recover cooldown
        self.rest_cooldowns = {}     # for !rest cooldown
        self.heartbeat.start()
        # Ensure database has heartbeat_dm column (default ON)
        self.bot.loop.create_task(self.init_db_column())

    async def init_db_column(self):
        await self.bot.wait_until_ready()
        db = self.bot.db
        async with db.execute("PRAGMA table_info(users)") as cur:
            cols = [row[1] for row in await cur.fetchall()]
        if "heartbeat_dm" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN heartbeat_dm INTEGER DEFAULT 1")
            await db.commit()

    def cog_unload(self):
        self.heartbeat.cancel()

    # ==========================================
    # HEARTBEAT (every 20 min, with DM toggle)
    # ==========================================
    @tasks.loop(minutes=20.0)
    async def heartbeat(self):
        db = self.bot.db
        async with db.execute("SELECT user_id, hp, vitality, rank, heartbeat_dm FROM users") as cursor:
            users = await cursor.fetchall()

        for user in users:
            u_id, current_hp, current_vit, rank, dm_enabled = user
            # Determine regen amount based on rank
            if "Second-Rate" in rank:
                regen = 100
            elif "Third-Rate" in rank:
                regen = 50
            else:
                regen = 25

            max_stats = get_max_stats(rank)
            limit_hp = max_stats["max_hp"]
            limit_vit = max_stats["max_vit"]

            new_hp = min(current_hp + regen, limit_hp)
            new_vit = min(current_vit + regen, limit_vit)

            if new_hp != current_hp or new_vit != current_vit:
                await db.execute(
                    "UPDATE users SET hp = ?, vitality = ? WHERE user_id = ?",
                    (new_hp, new_vit, u_id)
                )
                # Send DM only if user has not disabled it
                if dm_enabled:
                    user_obj = self.bot.get_user(u_id)
                    if user_obj:
                        try:
                            await user_obj.send(
                                f"🌿 **Heavenly Recovery**\n"
                                f"You regain **{new_hp - current_hp} HP** and **{new_vit - current_vit} Vitality**.\n"
                                f"Current: {new_hp} HP / {new_vit} Vitality"
                            )
                        except discord.Forbidden:
                            pass
        await db.commit()

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # ==========================================
    # TOGGLE HEARTBEAT DMs (feature 3)
    # ==========================================
    @commands.hybrid_command(name="toggle_dm", description="Enable/disable heartbeat recovery DMs")
    async def toggle_dm(self, ctx):
        db = self.bot.db
        async with db.execute("SELECT heartbeat_dm FROM users WHERE user_id = ?", (ctx.author.id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)
        current = row[0]
        new = 0 if current else 1
        await db.execute("UPDATE users SET heartbeat_dm = ? WHERE user_id = ?", (new, ctx.author.id))
        await db.commit()
        status = "enabled" if new else "disabled"
        await ctx.send(f"✅ Heartbeat DMs **{status}**.", ephemeral=True)

    # ==========================================
    # RECOVER (active meditation) – polish 1,2,4,7
    # ==========================================
    @commands.hybrid_command(name="recover", description="Active meditation: Restore 25 Vit & 5 Ki in 60s.")
    async def recover(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

        # Cooldown check (feature 7 – shown in meditate, but also here)
        if user_id in self.cooldowns:
            if now < self.cooldowns[user_id]:
                diff = self.cooldowns[user_id] - now
                return await ctx.send(f"❌ Your soul is still stabilizing. Wait **{int(diff.total_seconds())}s** before meditating again.", ephemeral=True)

        if user_id in self.meditating:
            return await ctx.send("🧘 You are already in deep meditation.", ephemeral=True)

        self.meditating.add(user_id)
        if not hasattr(self.bot, 'is_meditating'):
            self.bot.is_meditating = set()
        self.bot.is_meditating.add(user_id)

        msg = await ctx.send("🧘 You enter a state of deep meditation. Your senses dull as your Ki stabilizes... (60s)")

        # Polish 1: progress bar
        total_time = 60
        for remaining in range(total_time, -1, -10):
            await asyncio.sleep(10)
            percent = (remaining / total_time) * 100
            filled = int(percent / 10)  # 10 segments
            bar = "█" * filled + "░" * (10 - filled)
            if remaining > 0:
                await msg.edit(content=f"🧘 Meditating... `[{bar}]` **{remaining}s** left.")
            else:
                await msg.edit(content="🧘 Meditating... `[██████████]` **0s** left. Almost there...")

        db = self.bot.db
        async with db.execute("SELECT rank, ki, background FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            self.meditating.remove(user_id)
            self.bot.is_meditating.remove(user_id)
            return await ctx.send("❌ You are not registered. Use `!start` first.", ephemeral=True)

        rank, current_ki, background = row
        max_stats = get_max_stats(rank)
        ki_cap = max_stats["ki_cap"]
        vit_cap = max_stats["max_vit"]

        # Add 25 Vitality, 5 Ki (Hermit bonus: +10/+10)
        vit_gain = 25
        ki_gain = 5
        if background == "Hermit":
            vit_gain = 35
            ki_gain = 15

        new_vit = min(vit_cap, (await db.execute("SELECT vitality FROM users WHERE user_id=?", (user_id,))).fetchone()[0] + vit_gain)
        new_ki = min(ki_cap, current_ki + ki_gain)

        await db.execute("UPDATE users SET vitality = ?, ki = ? WHERE user_id = ?", (new_vit, new_ki, user_id))
        await db.commit()

        self.meditating.remove(user_id)
        self.bot.is_meditating.remove(user_id)
        self.cooldowns[user_id] = now + datetime.timedelta(minutes=5)

        bonus_text = " (+Hermit bonus)" if background == "Hermit" else ""
        await msg.edit(content=f"✨ {ctx.author.mention}, you open your eyes as refreshing energy flows through your meridians! (+{vit_gain} Vitality, +{ki_gain} Ki{bonus_text})")

    # ==========================================
    # CANCEL MEDITATION
    # ==========================================
    @commands.hybrid_command(name="cancel", description="Cancel your active meditation.")
    async def cancel_meditation(self, ctx):
        user_id = ctx.author.id
        if user_id not in self.meditating:
            return await ctx.send("❌ You are not meditating.", ephemeral=True)
        self.meditating.remove(user_id)
        self.bot.is_meditating.remove(user_id)
        await ctx.send("🧘 You snap out of your meditation early.", ephemeral=True)

    # ==========================================
    # MEDITATE (check next heartbeat) – polish 5 & 7
    # ==========================================
    @commands.hybrid_command(name="meditate", description="Check natural recovery status and predicted gains.")
    async def meditate_status(self, ctx):
        next_it = self.heartbeat.next_iteration
        if not next_it:
            return await ctx.send("Heartbeat is not scheduled yet.", ephemeral=True)

        now = datetime.datetime.now(datetime.timezone.utc)
        time_left = next_it - now
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)

        db = self.bot.db
        async with db.execute("SELECT rank, ki, vitality, hp FROM users WHERE user_id = ?", (ctx.author.id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        rank, ki, vit, hp = row
        max_stats = get_max_stats(rank)
        ki_cap = max_stats["ki_cap"]
        vit_cap = max_stats["max_vit"]
        hp_cap = max_stats["max_hp"]

        # Regen amount (same as heartbeat)
        if "Second-Rate" in rank:
            regen = 100
        elif "Third-Rate" in rank:
            regen = 50
        else:
            regen = 25

        # Ki progress to next rank (polish 5 – simplified)
        ki_progress = int((ki / ki_cap) * 100) if ki_cap > 0 else 0

        # Recover cooldown remaining (polish 7)
        recover_cd = ""
        if ctx.author.id in self.cooldowns:
            cd_until = self.cooldowns[ctx.author.id]
            if datetime.datetime.now() < cd_until:
                cd_rem = int((cd_until - datetime.datetime.now()).total_seconds())
                recover_cd = f"\n⏳ `!recover` ready in **{cd_rem}s**"

        embed = discord.Embed(
            title="🧘 Meditation Status",
            description=f"The heavens will breathe again in **{minutes}m {seconds}s**.",
            color=0x700000
        )
        embed.add_field(
            name="Next Recovery",
            value=f"Restores **{regen} HP** and **{regen} Vitality**.",
            inline=False
        )
        embed.add_field(
            name="Your Progress",
            value=f"🩸 HP: {hp}/{hp_cap}\n❤️ Vit: {vit}/{vit_cap}\n✨ Ki: {ki}/{ki_cap} ({ki_progress}% to next stage)",
            inline=False
        )
        if recover_cd:
            embed.add_field(name="Cooldowns", value=recover_cd, inline=False)
        embed.set_footer(text="Use `!toggle_dm` to enable/disable heartbeat DMs.")
        await ctx.send(embed=embed, ephemeral=True)

    # ==========================================
    # NEW COMMAND: !focus (convert Vitality to Ki)
    # ==========================================
    @commands.hybrid_command(name="focus", description="Convert 10 Vitality into 5 Ki. 5 min cooldown.")
    async def focus(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

        # Cooldown check
        if hasattr(self, 'focus_cooldowns') and user_id in self.focus_cooldowns:
            if now < self.focus_cooldowns[user_id]:
                diff = self.focus_cooldowns[user_id] - now
                return await ctx.send(f"❌ Your mind is exhausted. Wait **{int(diff.total_seconds())}s** before focusing again.", ephemeral=True)

        db = self.bot.db
        async with db.execute("SELECT vitality, ki, rank FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)
        vit, ki, rank = row
        max_stats = get_max_stats(rank)
        vit_cap = max_stats["max_vit"]
        ki_cap = max_stats["ki_cap"]

        if vit < 10:
            return await ctx.send(f"❌ You need at least 10 Vitality to focus. (You have {vit})", ephemeral=True)

        new_vit = vit - 10
        new_ki = min(ki_cap, ki + 5)

        await db.execute("UPDATE users SET vitality = ?, ki = ? WHERE user_id = ?", (new_vit, new_ki, user_id))
        await db.commit()

        if not hasattr(self, 'focus_cooldowns'):
            self.focus_cooldowns = {}
        self.focus_cooldowns[user_id] = now + datetime.timedelta(minutes=5)

        await ctx.send(f"🌀 You focus your inner energy, converting **10 Vitality** into **5 Ki**!\n"
                       f"New Vitality: {new_vit} / {vit_cap}\n"
                       f"New Ki: {new_ki} / {ki_cap}")

    # ==========================================
    # NEW COMMAND: !rest (instant small heal, 1h cooldown)
    # ==========================================
    @commands.hybrid_command(name="rest", description="Instantly restore 10 HP and 10 Vitality. 1 hour cooldown.")
    async def rest(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

        if user_id in self.rest_cooldowns:
            if now < self.rest_cooldowns[user_id]:
                diff = self.rest_cooldowns[user_id] - now
                return await ctx.send(f"❌ You can rest again in **{int(diff.total_seconds()//60)}m {int(diff.total_seconds()%60)}s**.", ephemeral=True)

        db = self.bot.db
        async with db.execute("SELECT hp, vitality, rank FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)
        hp, vit, rank = row
        max_stats = get_max_stats(rank)
        hp_cap = max_stats["max_hp"]
        vit_cap = max_stats["max_vit"]

        new_hp = min(hp_cap, hp + 10)
        new_vit = min(vit_cap, vit + 10)

        await db.execute("UPDATE users SET hp = ?, vitality = ? WHERE user_id = ?", (new_hp, new_vit, user_id))
        await db.commit()

        self.rest_cooldowns[user_id] = now + datetime.timedelta(hours=1)
        await ctx.send(f"🛌 You rest for a moment, regaining **10 HP** and **10 Vitality**.\n"
                       f"HP: {new_hp}/{hp_cap} | Vit: {new_vit}/{vit_cap}")

async def setup(bot):
    await bot.add_cog(Mechanics(bot))