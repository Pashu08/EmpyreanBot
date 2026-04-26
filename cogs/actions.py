import discord
from discord.ext import commands
import sqlite3
import random

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.command(name="work")
    async def work(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT vitality, taels FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()

        if not user:
            return await ctx.send("❌ You haven't started your journey. Use `!start`.")
        
        vit, taels = user
        if vit < 10:
            return await ctx.send("❌ Your body is too exhausted to work. Rest or use a pulse.")

        # Gains and Costs
        gain = random.randint(5, 15)
        new_vit = vit - 10
        new_taels = taels + gain

        c.execute("UPDATE users SET vitality=?, taels=? WHERE user_id=?", (new_vit, new_taels, ctx.author.id))
        conn.commit()
        conn.close()

        # --- THE PROFESSIONAL BOX ---
        embed = discord.Embed(title="⚒️ Manual Labor", color=0x700000)
        embed.description = f"You spent hours performing grueling tasks for the local merchants."
        embed.add_field(name="Gained", value=f"💰 **+{gain}** Taels", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/100", inline=True)
        embed.set_footer(text=f"Current Total: {new_taels} Taels")
        
        await ctx.send(embed=embed)

    @commands.command(name="observe")
    async def observe(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT vitality, ki FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()

        if not user:
            return await ctx.send("❌ You haven't started your journey. Use `!start`.")

        vit, ki = user
        if vit < 10:
            return await ctx.send("❌ Your mind is too clouded by fatigue. You cannot observe.")

        # Gains and Costs
        gain = random.randint(3, 8)
        new_vit = vit - 10
        new_ki = ki + gain

        c.execute("UPDATE users SET vitality=?, ki=? WHERE user_id=?", (new_vit, new_ki, ctx.author.id))
        conn.commit()
        conn.close()

        # --- THE PROFESSIONAL BOX ---
        embed = discord.Embed(title="👁️ Deep Observation", color=0x00AABB)
        embed.description = f"You sat in silence, watching the flow of the world and the breath of the heavens."
        embed.add_field(name="Ki Refined", value=f"✨ **+{gain}** Ki", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/100", inline=True)
        embed.set_footer(text=f"Current Progress: {new_ki}/100 Ki")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Actions(bot))
