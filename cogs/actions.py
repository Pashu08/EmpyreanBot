import discord
from discord.ext import commands
import sqlite3
import random

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # COMMAND: !work (The Tael Grind)
    # ==========================================
    @commands.command()
    async def work(self, ctx):
        """The Mortal Struggle for money."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, vitality FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("Use !start first.")
        if user[1] < 10: return await ctx.send("❌ You are too exhausted to work. Rest your body.")

        # --- Random earnings logic ---
        income = random.randint(5, 15)
        
        # --- Applying the Blueprint Background Logic ---
        if user[0] == "Laborer":
            income = int(income * 0.5) # 50% Tax
            msg = f"🔨 [Laborer] You worked the docks. After the foreman's cut, you earned **{income} Taels**."
        elif user[0] == "Urchin" and random.random() < 0.1:
            income = 0 # 10% Mugging chance
            msg = "💸 [Urchin] A group of thugs cornered you in an alley! You lost your day's earnings."
        else:
            msg = f"💰 You completed your labor and earned **{income} Taels**."

        c.execute("UPDATE users SET taels = taels + ?, vitality = vitality - 10 WHERE user_id = ?", (income, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(msg)

    # ==========================================
    # COMMAND: !observe (The Path to Ki)
    # ==========================================
    @commands.command()
    async def observe(self, ctx):
        """The path to gathering Ki."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, vitality FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("Use !start first.")
        if user[1] < 10: return await ctx.send("❌ Your mind is too weary to focus on the world's flow.")

        # --- Ki Gain Logic ---
        gain = random.randint(5, 10)
        
        # --- Hermit Bonus Logic ---
        if user[0] == "Hermit":
            gain = int(gain * 1.2) # +20% Ki
            msg = f"🧘 [Hermit] Your pure heart resonates with the world. Gained **{gain} Ki**."
        else:
            msg = f"✨ You observed the flow of nature and gathered **{gain} Ki**."

        c.execute("UPDATE users SET ki = ki + ?, vitality = vitality - 10 WHERE user_id = ?", (gain, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(msg)

    # ==========================================
    # COMMAND: !rest (Vitality Recovery)
    # ==========================================
    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user) # 5 Min Cooldown
    async def rest(self, ctx):
        """Rest to recover Vitality."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT vitality FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("Use !start first.")
        
        if user[0] >= 100:
            self.rest.reset_cooldown(ctx)
            return await ctx.send("Your body is already at its peak. You do not need rest.")

        # --- Recovery Logic ---
        new_vit = min(100, user[0] + 20)
        c.execute("UPDATE users SET vitality = ? WHERE user_id = ?", (new_vit, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(f"🛌 You found a quiet spot to rest. Your Vitality is now **{new_vit}/100**.")

    @rest.error
    async def rest_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            minutes = int(error.retry_after // 60)
            seconds = int(error.retry_after % 60)
            await ctx.send(f"⏳ You cannot rest again so soon. Wait **{minutes}m {seconds}s**.")

async def setup(bot):
    await bot.add_cog(Actions(bot))
