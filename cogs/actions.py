import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # Discord V2 Slash Command for Work
    @app_commands.command(name="work", description="Perform manual labor for Taels")
    @app_commands.checks.cooldown(1, 5.0)
    async def work(self, interaction: discord.Interaction):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT vitality, taels, rank FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()

        if not user:
            return await interaction.response.send_message("❌ Use `!start` first.", ephemeral=True)
        
        vit, taels, rank = user
        max_vit = 300 if "Third-Rate" in rank else 100

        if vit < 10:
            return await interaction.response.send_message(f"❌ Your body is too exhausted. ({vit}/{max_vit})", ephemeral=True)

        gain = random.randint(5, 15)
        new_vit = max(0, vit - 10)
        new_taels = taels + gain

        c.execute("UPDATE users SET vitality=?, taels=? WHERE user_id=?", (new_vit, new_taels, interaction.user.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="⚒️ Manual Labor", color=0x700000)
        embed.description = f"You spent hours performing grueling tasks for the local merchants."
        embed.add_field(name="Gained", value=f"💰 **+{gain}** Taels", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        embed.set_footer(text=f"Current Total: {new_taels} Taels")
        
        await interaction.response.send_message(embed=embed)

    # Discord V2 Slash Command for Observe
    @app_commands.command(name="observe", description="Refine your Ki through meditation")
    @app_commands.checks.cooldown(1, 5.0)
    async def observe(self, interaction: discord.Interaction):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT vitality, ki, rank FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()

        if not user:
            return await interaction.response.send_message("❌ Use `!start` first.", ephemeral=True)

        vit, ki, rank = user
        max_vit = 300 if "Third-Rate" in rank else 100
        ki_goal = 300 if "Third-Rate" in rank else 100

        if vit < 10:
            return await interaction.response.send_message(f"❌ Your mind is too clouded by fatigue. ({vit}/{max_vit})", ephemeral=True)

        gain = random.randint(3, 8)
        new_vit = max(0, vit - 10)
        new_ki = ki + gain

        c.execute("UPDATE users SET vitality=?, ki=? WHERE user_id=?", (new_vit, new_ki, interaction.user.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="👁️ Deep Observation", color=0x00AABB)
        embed.description = f"You sat in silence, watching the flow of the world and the breath of the heavens."
        embed.add_field(name="Ki Refined", value=f"✨ **+{gain}** Ki", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        embed.set_footer(text=f"Current Progress: {new_ki}/{ki_goal} Ki")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Actions(bot))
