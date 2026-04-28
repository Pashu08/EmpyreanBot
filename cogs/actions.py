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

    @app_commands.command(name="work", description="Perform manual labor for Taels")
    @app_commands.checks.cooldown(1, 5.0)
    async def work(self, interaction: discord.Interaction):
        conn = self.get_db()
        c = conn.cursor()
        # Added background and mastery to the selection for Phase 2 perks
        user = c.execute("SELECT vitality, taels, rank, background, mastery, active_tech FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()

        if not user:
            return await interaction.response.send_message("❌ Use `!start` first.", ephemeral=True)
        
        vit, taels, rank, bg, mastery, tech = user
        
        # --- PHASE 2 DYNAMIC CAPS ---
        if "Second-Rate" in rank: max_vit = 600
        elif "Third-Rate" in rank: max_vit = 300
        else: max_vit = 100

        if vit < 10:
            return await interaction.response.send_message(f"❌ Your body is too exhausted. ({vit}/{max_vit})", ephemeral=True)

        gain = random.randint(5, 15)
        new_vit = max(0, vit - 10)
        new_taels = taels + gain
        
        mastery_msg = ""
        # LABORER PERK: 10% chance to gain Mastery while working
        if bg == "Laborer" and tech != "None" and mastery < 100:
            if random.random() < 0.10:
                mastery_gain = 0.5
                new_mastery = min(100.0, mastery + mastery_gain)
                c.execute("UPDATE users SET mastery=? WHERE user_id=?", (new_mastery, interaction.user.id))
                mastery_msg = f"\n✨ **Laborer's Insight:** Your hard work refined your {tech}! (+0.5% Mastery)"

        c.execute("UPDATE users SET vitality=?, taels=? WHERE user_id=?", (new_vit, new_taels, interaction.user.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="⚒️ Manual Labor", color=0x700000)
        embed.description = f"You spent hours performing grueling tasks for the local merchants.{mastery_msg}"
        embed.add_field(name="Gained", value=f"💰 **+{gain}** Taels", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        embed.set_footer(text=f"Current Total: {new_taels} Taels")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="observe", description="Refine your Ki through meditation")
    @app_commands.checks.cooldown(1, 5.0)
    async def observe(self, interaction: discord.Interaction):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT vitality, ki, rank FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()

        if not user:
            return await interaction.response.send_message("❌ Use `!start` first.", ephemeral=True)

        vit, ki, rank = user
        
        # --- PHASE 2 DYNAMIC CAPS ---
        if "Second-Rate" in rank:
            max_vit, ki_cap = 600, 3000
        elif "Third-Rate" in rank:
            max_vit, ki_cap = 300, 1000
        else:
            max_vit, ki_cap = 100, 100

        if vit < 10:
            return await interaction.response.send_message(f"❌ Your mind is too clouded by fatigue. ({vit}/{max_vit})", ephemeral=True)

        gain = random.randint(3, 8)
        new_vit = max(0, vit - 10)
        new_ki = min(ki_cap, ki + gain) # Respect the Realm Cap

        c.execute("UPDATE users SET vitality=?, ki=? WHERE user_id=?", (new_vit, new_ki, interaction.user.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="👁️ Deep Observation", color=0x00AABB)
        embed.description = f"You sat in silence, watching the flow of the world and the breath of the heavens."
        embed.add_field(name="Ki Refined", value=f"✨ **+{gain}** Ki", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        embed.set_footer(text=f"Current Progress: {new_ki}/{ki_cap} Ki")

        await interaction.response.send_message(embed=embed)

    @work.error
    @observe.error
    async def action_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ **Focus your breathing.** Wait {error.retry_after:.1f}s.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Actions(bot))
