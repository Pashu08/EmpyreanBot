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
        self.bot.loop.create_task(self.start_heartbeat_safe())

    async def start_heartbeat_safe(self):
        await self.bot.wait_until_ready()
        await self.init_db_column()
        self.heartbeat.start()

    async def init_db_column(self):
        db = self.bot.db
        async with db.execute("PRAGMA table_info(users)") as cur:
            cols = [row[1] for row in await cur.fetchall()]
        if "heartbeat_dm" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN heartbeat_dm INTEGER DEFAULT 1")
            await db.commit()

    def cog_unload(self):
        self.heartbeat.cancel()

    # ========== HEARTBEAT (with DM toggle) ==========
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
                            await user_obj.send(f"🌿 **Heavenly Recovery**\nYou regain **{new_hp - current_hp} HP** and **{new_vit - current_vit} Vitality**.\nCurrent: {new_hp} HP / {new_vit} Vitality")
                        except discord.Forbidden:
                            pass
        await db.commit()

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # ========== TOGGLE DM ==========
    @commands.hybrid_command(name="toggle_dm", description="Enable/disable heartbeat DMs")
    async def toggle_dm(self, ctx):
        db = self.bot.db
        async with db.execute("SELECT heartbeat_dm FROM users WHERE user_id = ?", (ctx.author.id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)
        new = 0 if row[0] else 1
        await db.execute("UPDATE users SET heartbeat_dm = ? WHERE user_id = ?", (new, ctx.author.id))
        await db.commit()
        await ctx.send(f"✅ Heartbeat DMs **{'enabled' if new else 'disabled'}**.", ephemeral=True)

    # ========== RECOVER (simple version, no progress bar, no hermit bonus) ==========
    @commands.hybrid_command(name="recover", description="Active meditation: restore 25 Vit & 5 Ki in 60s.")
    async def recover(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()
        if user_id in self.cooldowns and now < self.cooldowns[user_id]:
            diff = self.cooldowns[user_id] - now
            return await ctx.send(f"❌ Wait {int(diff.total_seconds())}s.", ephemeral=True)
        if user_id in self.meditating:
            return await ctx.send("🧘 Already meditating.", ephemeral=True)
        self.meditating.add(user_id)
        msg = await ctx.send("🧘 Meditating for 60s...")
        for i in range(60, 0, -10):
            await asyncio.sleep(10)
            await msg.edit(content=f"🧘 {i}s left...")
        self.meditating.remove(user_id)
        db = self.bot.db
        async with db.execute("SELECT rank, ki FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return await ctx.send("❌ Use !start first.")
        rank, ki = row
        max_stats = get_max_stats(rank)
        new_vit = min(max_stats["max_vit"], (await db.execute("SELECT vitality FROM users WHERE user_id=?", (user_id,))).fetchone()[0] + 25)
        new_ki = min(max_stats["ki_cap"], ki + 5)
        await db.execute("UPDATE users SET vitality = ?, ki = ? WHERE user_id = ?", (new_vit, new_ki, user_id))
        await db.commit()
        self.cooldowns[user_id] = now + datetime.timedelta(minutes=5)
        await msg.edit(content=f"✨ Recovered +25 Vit, +5 Ki.")

    # ========== CANCEL ==========
    @commands.hybrid_command(name="cancel", description="Cancel active meditation")
    async def cancel(self, ctx):
        if ctx.author.id in self.meditating:
            self.meditating.remove(ctx.author.id)
            await ctx.send("🧘 Meditation cancelled.")
        else:
            await ctx.send("❌ Not meditating.")

    # ========== MEDITATE (simple) ==========
    @commands.hybrid_command(name="meditate", description="Check next heartbeat")
    async def meditate(self, ctx):
        next_it = self.heartbeat.next_iteration
        if not next_it:
            return await ctx.send("Heartbeat not ready.")
        now = datetime.datetime.now(datetime.timezone.utc)
        left = next_it - now
        minutes = int(left.total_seconds() // 60)
        seconds = int(left.total_seconds() % 60)
        await ctx.send(f"🧘 Next recovery in {minutes}m {seconds}s.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Mechanics(bot))