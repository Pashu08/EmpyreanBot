import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import asyncio
import datetime

# --- PAVILION UI ---
class PavilionView(discord.ui.View):
    def __init__(self, ctx, member_id, db_func):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.member_id = member_id
        self.get_db = db_func
        
        # Detailed Explanations for the Seeker
        self.techniques = {
            "Flowing Cloud Steps": "💨 **Focus:** Dodge & Agility\n*Mastery increases your natural chance to evade strikes in combat.*",
            "Swift Wind Kick": "🦶 **Focus:** Damage & Speed\n*Mastery increases your total damage output and strike frequency.*",
            "Golden Bell Shield": "🔔 **Focus:** Defense & Tanking\n*Mastery reduces the damage you take from physical blows significantly.*",
            "Vajra Guard Mantra": "🧘 **Focus:** Vitality Regeneration\n*Mastery boosts your natural health and energy recovery rates.*"
        }
        self.create_buttons()

    def create_buttons(self):
        for name in self.techniques.keys():
            btn = discord.ui.Button(label=name, style=discord.ButtonStyle.primary, custom_id=name)
            btn.callback = self.select_tech
            self.add_item(btn)

    async def select_tech(self, interaction: discord.Interaction):
        if interaction.user.id != self.member_id:
            return await interaction.response.send_message("You cannot choose for another.", ephemeral=True)
            
        tech_name = interaction.data['custom_id']
        conn = self.get_db()
        c = conn.cursor()
        
        c.execute("UPDATE users SET active_tech = ?, mastery = 0.0 WHERE user_id = ?", (tech_name, self.member_id))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="📜 Technique Bound",
            description=f"You have begun studying **{tech_name}**.\n\n"
                        f"{self.techniques[tech_name]}\n\n"
                        f"*Mastery:* **0.0%**\n*Goal:* Reach **50%** to attempt your first Breakthrough.",
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
    # HEARTBEAT LOOP (Automatic Recovery)
    # ==========================================
    @tasks.loop(minutes=10.0)
    async def heartbeat(self):
        conn = self.get_db()
        c = conn.cursor()
        users = c.execute("SELECT user_id, hp, vitality, rank FROM users").fetchall()
        
        for user in users:
            u_id, current_hp, current_vit, rank = user
            if "Second-Rate" in rank: regen = 25
            elif "Third-Rate" in rank: regen = 15
            else: regen = 5
            
            caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 300, "Second-Rate Warrior": 600}
            limit = caps.get(rank, 1000)
            
            new_hp = min(current_hp + regen, limit)
            new_vit = min(current_vit + regen, limit)
            
            if new_hp != current_hp or new_vit != current_vit:
                c.execute("UPDATE users SET hp = ?, vitality = ? WHERE user_id = ?", (new_hp, new_vit, u_id))
        
        conn.commit()
        conn.close()

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()

    # ==========================================
    # HYBRID COMMANDS (!pavilion)
    # ==========================================
    @commands.hybrid_command(name="pavilion", description="Enter the library to choose foundational techniques.")
    async def pavilion(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT rank, ki, active_tech, mastery FROM users WHERE user_id = ?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        rank, ki, active_tech, mastery = user

        # 1. Check if user meets the Ki requirement
        if "Mortal" in rank and ki < 100:
            return await ctx.send("❌ The scrolls are sealed. You need **100 Ki** to understand these foundations.", ephemeral=True)

        # 2. Setup the descriptions for the display
        pavilion_desc = "**The Library contains the following foundations:**\n\n"
        pavilion_desc += "💨 **Flowing Cloud Steps**\n*Focus: Dodge & Agility*\n\n"
        pavilion_desc += "🦶 **Swift Wind Kick**\n*Focus: Damage & Speed*\n\n"
        pavilion_desc += "🔔 **Golden Bell Shield**\n*Focus: Defense & Tanking*\n\n"
        pavilion_desc += "🧘 **Vajra Guard Mantra**\n*Focus: Vitality Regeneration*"

        # 3. Logic for players who ALREADY have a technique
        if active_tech != "None":
            embed = discord.Embed(
                title="🏮 Pavilion: Current Focus",
                description=f"You are currently focusing on **{active_tech}**.\n"
                            f"**Current Mastery:** `{mastery}%` / 100%\n\n"
                            f"*To switch techniques, you must complete your current study or reset your progress.*",
                color=0x700000
            )
            embed.add_field(name="Available for Future Study", value=pavilion_desc)
            return await ctx.send(embed=embed)

        # 4. Logic for players choosing for the first time
        view = PavilionView(ctx, ctx.author.id, self.get_db)
        embed = discord.Embed(
            title="🏮 Pavilion of Hidden Scrolls",
            description=f"The air is thick with the scent of old paper. Four foundational scrolls sit before you.\n\n{pavilion_desc}",
            color=0x700000
        )
        embed.set_footer(text="Choose a path to begin your specialized training.")
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="meditate", description="Check natural recovery status")
    async def meditate_status(self, ctx):
        next_it = self.heartbeat.next_iteration
        if next_it:
            now = datetime.datetime.now(datetime.timezone.utc)
            time_left = next_it - now
            minutes = int(time_left.total_seconds() // 60)
            seconds = int(time_left.total_seconds() % 60)
            await ctx.send(
                f"🧘 The heavens will breathe again in **{minutes}m {seconds}s**, restoring your Vitality.", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Mechanics(bot))
