import discord
from discord.ext import commands, tasks
from discord import app_commands # Added for V2
import sqlite3
import asyncio

class Mechanics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.heartbeat.start() # Starts the auto-recovery loop

    def cog_unload(self):
        self.heartbeat.cancel()

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # THE HEARTBEAT: Runs every 10 minutes
    # ==========================================
    @tasks.loop(minutes=10.0)
    async def heartbeat(self):
        """Naturally restores HP and Vitality based on Rank."""
        conn = self.get_db()
        c = conn.cursor()
        
        users = c.execute("SELECT user_id, rank, hp, vitality FROM users").fetchall()
        
        for user in users:
            u_id, rank, current_hp, current_vit = user
            
            # --- UPDATED DYNAMIC CAPS FOR V2 ---
            if "Second-Rate" in rank:
                max_val = 600
                regen = 25 # Superior recovery for Second-Rate
            elif "Third-Rate" in rank:
                max_val = 300
                regen = 15 # Accelerated recovery for Warriors
            else:
                max_val = 100
                regen = 5  # Standard Mortal recovery
            
            new_hp = min(current_hp + regen, max_val)
            new_vit = min(current_vit + regen, max_val)
            
            if new_hp != current_hp or new_vit != current_vit:
                c.execute("""
                    UPDATE users 
                    SET hp = ?, vitality = ? 
                    WHERE user_id = ?
                """, (new_hp, new_vit, u_id))
        
        conn.commit()
        conn.close()

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # --- DISCORD V2 SLASH COMMANDS ---
    @app_commands.command(name="meditate", description="Check how much time until the next natural recovery heartbeat")
    async def meditate_status(self, interaction: discord.Interaction):
        """A V2 utility command for players to check the heartbeat status."""
        next_it = self.heartbeat.next_iteration
        if next_it:
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            time_left = next_it - now
            minutes = int(time_left.total_seconds() // 60)
            seconds = int(time_left.total_seconds() % 60)
            await interaction.response.send_message(
                f"🧘 The heavens will breathe again in **{minutes}m {seconds}s**, restoring your Vitality.", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message("The world's breath is currently still.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Mechanics(bot))
