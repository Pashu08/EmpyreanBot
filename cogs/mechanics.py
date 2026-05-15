import discord
from discord.ext import commands, tasks
import asyncio
import datetime
from utils.helpers import get_max_stats

class Mechanics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meditating = set()
        self.recover_cooldowns = {}      # user_id -> datetime
        self.focus_cooldowns = {}
        self.rest_cooldowns = {}
        # Start heartbeat in background after bot is ready
        self.bot.loop.create_task(self._delayed_start())

    async def _delayed_start(self):
        await self.bot.wait_until_ready()
        await self._init_db_column()
        self.heartbeat.start()

    async def _init_db_column(self):
        db = self.bot.db
        async with db.execute("PRAGMA table_info(users)") as cur:
            cols = [row[1] for row in await cur.fetchall()]
        if "heartbeat_dm" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN heartbeat_dm INTEGER DEFAULT 1")
            await db.commit()

    def cog_unload(self):
        self.heartbeat.cancel()

    # ========== HEARTBEAT (every 20 min, with DM toggle) ==========
    @tasks.loop(minutes=20.0)
    async def heartbeat(self):
        db = self.bot.db
        async with db.execute("SELECT user_id, hp, vitality, rank, heartbeat_dm FROM users") as cursor:
            users = await cursor.fetchall()
        for u_id, current_hp, current_vit, rank, dm_enabled in users:
            if "Second-Rate" in rank:
                regen = 100
            elif "Third-Rate" in rank:
                regen = 50
            else:
                regen = 25
            max_stats = get_max_stats(rank)
            new_hp = min(current_hp + regen, max_stats["max_hp"])
            new_vit = min(current_vit + regen, max_stats["max_vit"])
            if new_hp != current_hp or new_vit != current_vit:
                await db.execute(
                    "UPDATE users SET hp = ?, vitality = ? WHERE user_id = ?",
                    (new_hp, new_vit, u_id)
                )
                if dm_enabled:
                    user_obj = self.bot.get_user(u_id)
                    if user_obj:
                        try:
                            embed = discord.Embed(
                                title="🌿 Heavenly Recovery",
                                description=f"You regain **{new_hp - current_hp} HP** and **{new_vit - current_vit} Vitality**.\n"
                                            f"Current: {new_hp} HP / {new_vit} Vitality",
                                color=0x00AAFF
                            )
                            await user_obj.send(embed=embed)
                        except discord.Forbidden:
                            pass
        await db.commit()

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # ========== TOGGLE HEARTBEAT DMs ==========
    @commands.hybrid_command(name="toggle_dm", description="Enable/disable heartbeat recovery DMs")
    async def toggle_dm(self, ctx):
        db = self.bot.db
        async with db.execute("SELECT heartbeat_dm FROM users WHERE user_id = ?", (ctx.author.id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)
        new = 0 if row[0] else 1
        await db.execute("UPDATE users SET heartbeat_dm = ? WHERE user_id = ?", (new, ctx.author.id))
        await db.commit()
        embed = discord.Embed(title="✅ Heartbeat DM Toggle", description=f"Heartbeat DMs **{'enabled' if new else 'disabled'}**.", color=0x00FF00)
        await ctx.send(embed=embed, ephemeral=True)

    # ========== RECOVER (active meditation) ==========
    @commands.hybrid_command(name="recover", description="Meditate for 60s to restore Vitality and Ki")
    async def recover(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

        # Cooldown check (safe)
        if user_id in self.recover_cooldowns and now < self.recover_cooldowns[user_id]:
            remaining = int((self.recover_cooldowns[user_id] - now).total_seconds())
            embed = discord.Embed(title="⏳ Recovery on Cooldown", description=f"Please wait **{remaining} seconds**.", color=0xFFAA00)
            return await ctx.send(embed=embed, ephemeral=True)

        if user_id in self.meditating:
            embed = discord.Embed(title="🧘 Already Meditating", description="You are already in deep meditation.", color=0xFF5555)
            return await ctx.send(embed=embed, ephemeral=True)

        self.meditating.add(user_id)
        if not hasattr(self.bot, 'is_meditating'):
            self.bot.is_meditating = set()
        self.bot.is_meditating.add(user_id)

        # Initial message
        embed = discord.Embed(title="🧘 Meditation Begins", description="You enter a state of deep meditation... (60s)", color=0x9B59B6)
        msg = await ctx.send(embed=embed)

        total_time = 60
        for remaining in range(total_time, -1, -10):
            await asyncio.sleep(10)
            if remaining > 0:
                percent = (remaining / total_time) * 100
                filled = int(percent / 10)
                bar = "█" * filled + "░" * (10 - filled)
                embed = discord.Embed(title="🧘 Meditating", description=f"`[{bar}]` **{remaining}s** left...", color=0x9B59B6)
                await msg.edit(embed=embed)
            else:
                embed = discord.Embed(title="🧘 Meditation Complete", description="`[██████████]` **0s** – Almost there...", color=0x9B59B6)
                await msg.edit(embed=embed)

        self.meditating.remove(user_id)
        self.bot.is_meditating.remove(user_id)

        db = self.bot.db
        async with db.execute("SELECT rank, ki, background FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        rank, current_ki, background = row
        max_stats = get_max_stats(rank)
        ki_cap = max_stats["ki_cap"]
        vit_cap = max_stats["max_vit"]

        vit_gain = 25
        ki_gain = 5
        if background == "Hermit":
            vit_gain = 35
            ki_gain = 15

        # Get current vitality
        async with db.execute("SELECT vitality FROM users WHERE user_id=?", (user_id,)) as cur:
            vit_row = await cur.fetchone()
            current_vit = vit_row[0] if vit_row else 0

        new_vit = min(vit_cap, current_vit + vit_gain)
        new_ki = min(ki_cap, current_ki + ki_gain)

        await db.execute("UPDATE users SET vitality = ?, ki = ? WHERE user_id = ?", (new_vit, new_ki, user_id))
        await db.commit()

        # Set cooldown
        self.recover_cooldowns[user_id] = now + datetime.timedelta(minutes=5)

        bonus_text = " (+Hermit bonus)" if background == "Hermit" else ""
        embed = discord.Embed(
            title="✨ Meditation Complete",
            description=f"You regained **+{vit_gain} Vitality** and **+{ki_gain} Ki**{bonus_text}.\n"
                        f"Current: {new_vit} Vitality | {new_ki} Ki",
            color=0x00FFAA
        )
        await msg.edit(embed=embed)

    # ========== CANCEL MEDITATION ==========
    @commands.hybrid_command(name="cancel", description="Cancel active meditation")
    async def cancel_meditation(self, ctx):
        if ctx.author.id in self.meditating:
            self.meditating.remove(ctx.author.id)
            self.bot.is_meditating.remove(ctx.author.id)
            embed = discord.Embed(title="🧘 Meditation Cancelled", description="You snap out of your meditation early.", color=0xFFAA00)
            await ctx.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Not Meditating", description="You are not currently meditating.", color=0xFF5555)
            await ctx.send(embed=embed, ephemeral=True)

    # ========== MEDITATE STATUS (improved embed) ==========
    @commands.hybrid_command(name="meditate", description="Check next heartbeat and your progress")
    async def meditate_status(self, ctx):
        next_it = self.heartbeat.next_iteration
        if not next_it:
            return await ctx.send("Heartbeat not scheduled yet.", ephemeral=True)

        now = datetime.datetime.now(datetime.timezone.utc)
        left = next_it - now
        minutes = int(left.total_seconds() // 60)
        seconds = int(left.total_seconds() % 60)

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

        # Regen amount based on rank
        if "Second-Rate" in rank:
            regen = 100
        elif "Third-Rate" in rank:
            regen = 50
        else:
            regen = 25

        ki_progress = int((ki / ki_cap) * 100) if ki_cap else 0
        # Create progress bar for Ki
        bar_filled = int(ki_progress / 10)
        ki_bar = "█" * bar_filled + "░" * (10 - bar_filled)

        embed = discord.Embed(title="🧘 Meditation Status", description=f"Next heavenly breath in **{minutes}m {seconds}s**.", color=0x9B59B6)
        embed.add_field(name="🌿 Next Recovery", value=f"Restores **{regen} HP** and **{regen} Vitality**.", inline=False)
        embed.add_field(name="📊 Your Progress", value=f"🩸 **HP:** {hp}/{hp_cap}\n❤️ **Vitality:** {vit}/{vit_cap}\n✨ **Ki:** {ki}/{ki_cap} (`{ki_bar}` {ki_progress}%)", inline=False)
        embed.set_footer(text="Use `!toggle_dm` to enable/disable heartbeat DMs.")
        await ctx.send(embed=embed, ephemeral=True)

    # ========== FOCUS (convert Vitality to Ki) ==========
    @commands.hybrid_command(name="focus", description="Convert 10 Vitality into 5 Ki (5 min cooldown)")
    async def focus(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

        # Cooldown check
        if user_id in self.focus_cooldowns and now < self.focus_cooldowns[user_id]:
            remaining = int((self.focus_cooldowns[user_id] - now).total_seconds())
            embed = discord.Embed(title="⏳ Focus on Cooldown", description=f"Wait **{remaining} seconds**.", color=0xFFAA00)
            return await ctx.send(embed=embed, ephemeral=True)

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
            embed = discord.Embed(title="❌ Not Enough Vitality", description=f"You need 10 Vitality (you have {vit}).", color=0xFF5555)
            return await ctx.send(embed=embed, ephemeral=True)

        new_vit = vit - 10
        new_ki = min(ki_cap, ki + 5)

        await db.execute("UPDATE users SET vitality = ?, ki = ? WHERE user_id = ?", (new_vit, new_ki, user_id))
        await db.commit()

        self.focus_cooldowns[user_id] = now + datetime.timedelta(minutes=5)

        embed = discord.Embed(title="🌀 Focused Energy", description=f"You converted **10 Vitality** into **5 Ki**.\n"
                             f"Vitality: {new_vit}/{vit_cap}\nKi: {new_ki}/{ki_cap}", color=0x00AAFF)
        await ctx.send(embed=embed)

    # ========== REST (instant heal, 1h cooldown) ==========
    @commands.hybrid_command(name="rest", description="Instantly restore 10 HP and 10 Vitality (1 hour cooldown)")
    async def rest(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

        if user_id in self.rest_cooldowns and now < self.rest_cooldowns[user_id]:
            remaining = int((self.rest_cooldowns[user_id] - now).total_seconds())
            minutes_left = remaining // 60
            seconds_left = remaining % 60
            embed = discord.Embed(title="⏳ Rest on Cooldown", description=f"Next rest available in **{minutes_left}m {seconds_left}s**.", color=0xFFAA00)
            return await ctx.send(embed=embed, ephemeral=True)

        db = self.bot.db
        async with db.execute("SELECT hp, vitality, rank FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        hp, vit, rank = row
        max_stats = get_max_stats(rank)
        new_hp = min(max_stats["max_hp"], hp + 10)
        new_vit = min(max_stats["max_vit"], vit + 10)

        await db.execute("UPDATE users SET hp = ?, vitality = ? WHERE user_id = ?", (new_hp, new_vit, user_id))
        await db.commit()

        self.rest_cooldowns[user_id] = now + datetime.timedelta(hours=1)

        embed = discord.Embed(title="🛌 Rest Taken", description=f"You regain **10 HP** and **10 Vitality**.\n"
                             f"HP: {new_hp}/{max_stats['max_hp']} | Vitality: {new_vit}/{max_stats['max_vit']}", color=0x00FFAA)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Mechanics(bot))