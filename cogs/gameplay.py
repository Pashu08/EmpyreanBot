import discord
from discord.ext import commands
import sqlite3
import random

class Gameplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # This function opens the "Book of Life" (Database)
    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.command()
    async def stats(self, ctx):
        """Displays your current progress and status."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, taels, ki, vitality, item_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user:
            return await ctx.send("You have no status. Use !start to begin your struggle.")

        # Embeds make the bot look professional (Deep Red color)
        embed = discord.Embed(title=f"Status: {ctx.author.name}", color=0x700000)
        embed.add_field(name="Background", value=user[0], inline=True)
        embed.add_field(name="Vitality", value=f"❤️ {user[3]}/100", inline=True)
        embed.add_field(name="Taels", value=f"💰 {user[1]}", inline=True)
        embed.add_field(name="Ki", value=f"✨ {user[2]}", inline=True)
        embed.add_field(name="Innate Item", value=f"📦 {user[4]}", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def work(self, ctx):
        """The Mortal Struggle for money."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, vitality FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("Use !start first.")
        if user[1] < 10: return await ctx.send("❌ You are too exhausted to work. Rest your body.")

        # Random earnings between 5 and 15
        income = random.randint(5, 15)
        
        # Applying the Blueprint Logic
        if user[0] == "Laborer":
            income = int(income * 0.5) # The Tael Tax
            msg = f"🔨 [Laborer] You worked the docks. After the foreman's cut, you earned **{income} Taels**."
        elif user[0] == "Urchin" and random.random() < 0.1:
            income = 0 # The Mugger Logic (10% chance)
            msg = "💸 [Urchin] A group of thugs cornered you in an alley! You lost your day's earnings."
        else:
            msg = f"💰 You completed your labor and earned **{income} Taels**."

        # Update the database: Add money, subtract energy
        c.execute("UPDATE users SET taels = taels + ?, vitality = vitality - 10 WHERE user_id = ?", (income, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(msg)

    @commands.command()
    async def observe(self, ctx):
        """The path to gathering Ki."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, vitality FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("Use !start first.")
        if user[1] < 10: return await ctx.send("❌ Your mind is too weary to focus on the world's flow.")

        # Random Ki between 5 and 10
        gain = random.randint(5, 10)
        
        # Background Mechanic: Hermit Bonus (+20%)
        if user[0] == "Hermit":
            gain = int(gain * 1.2)
            msg = f"🧘 [Hermit] Your pure heart resonates with the world. Gained **{gain} Ki**."
        else:
            msg = f"✨ You observed the flow of nature and gathered **{gain} Ki**."

        # Update the database: Add Ki, subtract energy
        c.execute("UPDATE users SET ki = ki + ?, vitality = vitality - 10 WHERE user_id = ?", (gain, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(Gameplay(bot))
