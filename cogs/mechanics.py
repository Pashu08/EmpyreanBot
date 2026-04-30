import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import asyncio

# --- PAVILION UI ---
class PavilionView(discord.ui.View):
    def __init__(self, interaction, member_id, db_func):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.member_id = member_id
        self.get_db = db_func
        
        # Define the 4 Basic Techniques
        self.techniques = {
            "Flowing Cloud Steps": "💨 Focus: Dodge & Agility",
            "Swift Wind Kick": "🦶 Focus: Damage & Speed",
            "Golden Bell Shield": "🔔 Focus: Defense & Tanking",
            "Vajra Guard Mantra": "🧘 Focus: Vitality Regeneration"
        }
        self.create_buttons()

    def create_buttons(self):
        for name, desc in self.techniques.items():
            btn = discord.ui.Button(label=name, style=discord.ButtonStyle.primary, custom_id=name)
            btn.callback = self.select_tech
            self.add_item(btn)

    async self.select_tech(self, interaction: discord.Interaction):
        if interaction.user.id != self.member_id:
            return await interaction.response.send_message("You cannot choose for another.", ephemeral=True)
            
        tech_name = interaction.data['custom_id']
        conn = self.get_db()
        c = conn.cursor()
        
        # Bind the technique and set mastery to 0.0
        c.execute("UPDATE users SET active_tech = ?, mastery = 0.0 WHERE user_id = ?", (tech_name, self.member_id))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="📜 Technique Bound",
            description=f"You have begun studying **{tech_name}**.\n\n*Mastery:* **0.0%**\n*Goal:* Reach **50%** to attempt your first Breakthrough.",
            color=0x00FF00
        )
        await interaction.response.edit_message(embed=embed, view=None)

class Mechanics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.heartbeat.start()

    def cog_unload(self):
        self.heartbeat.cancel()

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # THE HEARTBEAT: Fixed for Dynamic Scaling
    # ==========================================
    @tasks.loop(minutes=10.0)
    async def heartbeat(self):
        """Naturally restores HP and Vitality based on Rank-scaled caps."""
        conn = self.get_db()
        c = conn.cursor()
        
        # We now pull the current values AND the limit we saved in cultivation.py
        users = c.execute("SELECT user_id, hp, vitality, rank FROM users").fetchall()
        
        for user in users:
            u_id, current_hp, current_vit, rank = user
            
            # Regen amount scales by rank
            if "Second-Rate" in rank: regen = 25
            elif "Third-Rate" in rank: regen = 15
            else: regen = 5
            
            # Since we don't store "Max_Cap" as a separate column yet, 
            # we use the logic: Mortal=100, 3rd=300, 2nd=600, etc.
            # but allow for the +200 boosts added during breakthroughs.
            caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 300, "Second-Rate Warrior": 600}
            base_cap = caps.get(rank, 1000)
            
            # We ensure regen doesn't exceed the player's natural limit
            new_hp = min(current_hp + regen, base_cap)
            new_vit = min(current_vit + regen, base_cap)
            
            if new_hp != current_hp or new_vit != current_vit:
                c.execute("UPDATE users SET hp = ?, vitality = ? WHERE user_id = ?", (new_hp, new_vit, u_id))
        
        conn.commit()
        conn.close()

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # ==========================================
    # THE PAVILION OF HIDDEN SCROLLS
    # ==========================================
    @app_commands.command(name="pavilion", description="Enter the library to choose or switch techniques.")
    async def pavilion(self, interaction: discord.Interaction):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT rank, ki, active_tech, profession FROM users WHERE user_id = ?", (interaction.user.id,)).fetchone()
        conn.close()

        if not user:
            return await interaction.response.send_message("❌ You have no presence in this world. Use `/start`.", ephemeral=True)

        rank, ki, active_tech, profession = user

        # 1. First Technique Requirement (Mortal & 100 Ki)
        if active_tech == "None":
            if "Mortal" in rank and ki < 100:
                return await interaction.response.send_message("❌ The scrolls remain sealed. You need **100 Ki** to comprehend these foundations.", ephemeral=True)
            
            view = PavilionView(interaction, interaction.user.id, self.get_db)
            embed = discord.Embed(
                title="🏮 Pavilion of Hidden Scrolls",
                description="The air is thick with the scent of old paper and incense. Four foundational scrolls sit before you.\n\n**Choose your path wisely.**",
                color=0x700000
            )
            return await interaction.response.send_message(embed=embed, view=view)

        # 2. Mastery Lock Check
        # (Future logic for switching innate moves will go here)
        await interaction.response.send_message(f"🧘 You are currently focusing on **{active_tech}**. You cannot look elsewhere until your mastery is complete.", ephemeral=True)

    @app_commands.command(name="meditate", description="Check natural recovery status")
    async def meditate_status(self, interaction: discord.Interaction):
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

async def setup(bot):
    await bot.add_cog(Mechanics(bot))
