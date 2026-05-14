import discord
from discord.ext import commands, tasks
import asyncio
import datetime
from utils.helpers import get_max_stats

class Mechanics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meditating = set()
        self.cooldowns = {}
        self.heartbeat.start()

    def cog_unload(self):
        self.heartbeat.cancel()

    # ==========================================
    # HEARTBEAT (automatic recovery every 10 min)
    # ==========================================
    @tasks.loop(minutes=10.0)
    async def heartbeat(self):
        db = self.bot.db
        async with db.execute("SELECT user_id, hp, vitality, rank FROM users") as cursor:
            users = await cursor.fetchall()

        for user in users:
            u_id, current_hp, current_vit, rank = user
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
                # Send DM notification (improvement A)
                user_obj = self.bot.get_user(u_id)
                if user_obj:
                    try:
                        await user_obj.send(
                            f"🌿 **Heavenly Recovery**\n"
                            f"You regain **{new_hp - current_hp} HP** and **{new_vit - current_vit} Vitality**.\n"
                            f"Current: {new_hp} HP / {new_vit} Vitality"
                        )
                    except discord.Forbidden:
                        pass  # can't DM, ignore
        await db.commit()

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # ==========================================
    # RECOVER (active meditation)
    # ==========================================
    @commands.hybrid_command(name="recover", description="Active meditation: Restore 25 Vit & 5 Ki in 60s.")
    async def recover(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

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

        # Countdown every 10 seconds (improvement B)
        for remaining in range(50, -1, -10):
            await asyncio.sleep(10)
            await msg.edit(content=f"🧘 Meditating... **{remaining}s** left.")

        await asyncio.sleep(10)  # final 10 seconds

        db = self.bot.db
        async with db.execute("SELECT rank, ki FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            self.meditating.remove(user_id)
            self.bot.is_meditating.remove(user_id)
            return await ctx.send("❌ You are not registered. Use `!start` first.", ephemeral=True)

        rank, current_ki = row
        max_stats = get_max_stats(rank)
        ki_cap = max_stats["ki_cap"]
        vit_cap = max_stats["max_vit"]

        # Add 25 Vitality and 5 Ki (improvement C)
        new_vit = min(vit_cap, (await db.execute("SELECT vitality FROM users WHERE user_id=?", (user_id,))).fetchone()[0] + 25)
        new_ki = min(ki_cap, current_ki + 5)

        await db.execute("UPDATE users SET vitality = ?, ki = ? WHERE user_id = ?", (new_vit, new_ki, user_id))
        await db.commit()

        self.meditating.remove(user_id)
        self.bot.is_meditating.remove(user_id)
        self.cooldowns[user_id] = now + datetime.timedelta(minutes=5)

        await msg.edit(content=f"✨ {ctx.author.mention}, you open your eyes as refreshing energy flows through your meridians! (+25 Vitality, +5 Ki)")

    # ==========================================
    # MEDITATE (check next heartbeat)
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

        # Get user's rank to predict recovery (improvement D)
        db = self.bot.db
        async with db.execute("SELECT rank FROM users WHERE user_id = ?", (ctx.author.id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        rank = row[0]
        if "Second-Rate" in rank:
            regen = 100
        elif "Third-Rate" in rank:
            regen = 50
        else:
            regen = 25

        embed = discord.Embed(
            title="🧘 Meditation Status",
            description=f"The heavens will breathe again in **{minutes}m {seconds}s**.",
            color=0x700000
        )
        embed.add_field(
            name="Next Recovery",
            value=f"Restores **{regen} HP** and **{regen} Vitality** (based on your rank).",
            inline=False
        )
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Mechanics(bot))