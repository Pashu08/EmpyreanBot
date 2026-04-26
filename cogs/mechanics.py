import discord
from discord.ext import commands, tasks
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
        
        # Fetch all users to process recovery
        users = c.execute("SELECT user_id, rank, hp, vitality FROM users").fetchall()
        
        for user in users:
            u_id, rank, current_hp, current_vit = user
            
            # Define Caps and Recovery Rates based on Rank
            if "Third-Rate" in rank:
                max_val = 300
                regen = 15 # Accelerated recovery for Warriors
            else:
                max_val = 100
                regen = 5  # Standard Mortal recovery
            
            # Calculate new values (without exceeding max)
            new_hp = min(current_hp + regen, max_val)
            new_vit = min(current_vit + regen, max_val)
            
            # Only update if they actually need healing/recovery
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

async def setup(bot):
    await bot.add_cog(Mechanics(bot))
