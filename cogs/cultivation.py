import discord
from discord.ext import commands
import sqlite3
import random

class Cultivation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # COMMAND: !breakthrough (Ascension)
    # ==========================================
    @commands.command()
    async def breakthrough(self, ctx):
        """Attempt to break the chains of The Bound."""
        conn = self.get_db()
        c = conn.cursor()
        # Fetching current rank/background and Ki
        user = c.execute("SELECT background, ki FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: 
            conn.close()
            return await ctx.send("Use !start first.")
        
        current_background = user[0]
        ki_amount = user[1]

        # --- Check if the user is still 'The Bound' ---
        # (This allows Laborers, Urchins, and Hermits to attempt the rank up)
        mortal_titles = ["Laborer", "Urchin", "Hermit", "The Bound (Mortal)"]
        if not any(title in current_background for title in mortal_titles):
            conn.close()
            return await ctx.send("You have already surpassed the Mortal realm.")

        # --- Requirement Check: 100 Ki ---
        if ki_amount < 100:
            conn.close()
            return await ctx.send(f"❌ Your Ki is only **{ki_amount}/100**. You lack the foundation to ascend.")

        await ctx.send("🌀 You circulate your Ki, attempting to shatter the limits of your mortal body...")

        # --- 50/50 Success Chance ---
        if random.random() < 0.5:
            # SUCCESS: Move to Third-Rate Warrior
            new_rank = "Third-Rate Warrior"
            c.execute("UPDATE users SET background = ?, ki = 0 WHERE user_id = ?", (new_rank, ctx.author.id))
            msg = f"✨ **SUCCESS!** ✨\n{ctx.author.mention}, you have broken your chains! You are now a **{new_rank}**."
        else:
            # FAILURE: 30% Ki Loss penalty
            penalty = int(ki_amount * 0.3)
            c.execute("UPDATE users SET ki = ki - ? WHERE user_id = ?", (penalty, ctx.author.id))
            msg = f"💥 **FAILURE!** 💥\nYour meridians recoiled! You suffered a backlash and lost **{penalty} Ki**."

        conn.commit()
        conn.close()
        await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
