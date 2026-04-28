import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import asyncio

# --- BREAKTHROUGH UI ---
class BreakthroughView(discord.ui.View):
    def __init__(self, interaction, member_id, db_func):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.member_id = member_id
        self.get_db = db_func
        self.stage = 1
        self.success_count = 0
        
        self.prompts = [
            {
                "text": "🌀 **Stage 1: The Gathering**\nYour Ki is swirling violently within your dantian. It feels like molten lead. How do you stabilize the flow?",
                "choices": ["Force it down", "Circulate slowly", "Let it overflow"]
            },
            {
                "text": "🔥 **Stage 2: The Core Heat**\nYour veins begin to glow. The heat is becoming unbearable. Your vision blurs. What is your next move?",
                "choices": ["Focus on breathing", "Ice the spirit", "Endure the pain"]
            },
            {
                "text": "⚡ **Stage 3: The Final Wall**\nYou see the bottleneck. A massive wall of shadow blocking your path to the next rank. Smash it!",
                "choices": ["All-out strike", "Look for a crack", "Pray for luck"]
            }
        ]
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        current_choices = self.prompts[self.stage-1]["choices"]
        for i, choice in enumerate(current_choices):
            btn = discord.ui.Button(label=choice, style=discord.ButtonStyle.secondary, custom_id=str(i))
            btn.callback = self.button_callback
            self.add_item(btn)

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member_id:
            return await interaction.response.send_message("This is not your tribulation.", ephemeral=True)

        if random.random() > 0.5:
            self.success_count += 1

        if self.stage < 3:
            self.stage += 1
            self.update_buttons()
            embed = discord.Embed(title="⚔️ Breakthrough in Progress", description=self.prompts[self.stage-1]["text"], color=0x700000)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.finish_breakthrough(interaction)

    async def finish_breakthrough(self, interaction):
        conn = self.get_db()
        c = conn.cursor()
        
        if self.success_count >= 2:
            user_data = c.execute("SELECT rank, item_id FROM users WHERE user_id=?", (self.member_id,)).fetchone()
            current_rank, current_item = user_data

            # PHASE 2 ASCENSION LOGIC
            if "Mortal" in current_rank:
                new_rank = "Third-Rate Warrior"
                new_cap = 300
            elif "Third-Rate" in current_rank:
                new_rank = "Second-Rate Warrior"
                new_cap = 600
            else:
                new_rank = "First-Rate Warrior"
                new_cap = 1000

            mutations = {"Torn Page": "Jade Scripture", "Black Coin": "Shadow Seal", "Glowing Fruit": "Verdant Bone"}
            new_item = mutations.get(current_item, current_item)

            # Reset Ki to 0 and set stage to Initial upon success
            c.execute("UPDATE users SET rank=?, stage='Initial', item_id=?, ki=0, vitality=?, hp=? WHERE user_id=?", 
                      (new_rank, new_item, new_cap, new_cap, self.member_id))
            
            result_embed = discord.Embed(title="🎊 REALM ASCENSION SUCCESS", 
                                        description=f"You have reached the **{new_rank}**!\nYour item has evolved into: **{new_item}**.\nYour limits have expanded to **{new_cap}**!", 
                                        color=0x00FF00)
        else:
            c.execute("UPDATE users SET ki = MAX(0, ki - 100) WHERE user_id=?", (self.member_id,))
            result_embed = discord.Embed(title="💀 BREAKTHROUGH FAILED", 
                                        description="The energy backfired. Your meridians are damaged and you lost 100 Ki.", 
                                        color=0xFF0000)
        
        conn.commit()
        conn.close()
        await interaction.response.edit_message(embed=result_embed, view=None)
        self.stop()

class Cultivation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="breakthrough", description="Attempt to reach a higher Major Realm")
    async def breakthrough(self, ctx):
        user_id = ctx.author.id
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT ki, rank, background, stage FROM users WHERE user_id=?", (user_id,)).fetchone()
        conn.close()

        if not user: 
            return await ctx.send("Start your journey first.", ephemeral=True)
        
        ki, rank, bg, stage = user
        
        # --- PHASE 2 REQUIREMENT LOGIC ---
        requirements = {
            "The Bound (Mortal)": 100,
            "Third-Rate Warrior": 1000,
            "Second-Rate Warrior": 3000
        }
        
        base_req = requirements.get(rank, 7500)
        
        # LABORER PERK: 15% lower Ki requirements
        if bg == "Laborer":
            base_req = int(base_req * 0.85)

        # STAGE LOCK: Must be at PEAK stage to attempt realm breakthrough
        if stage != "Peak":
            return await ctx.send(f"❌ You are currently in the **{stage}** stage. You must reach the **Peak** of your current realm first.", ephemeral=True)

        if ki < base_req:
            return await ctx.send(f"❌ Your foundation is insufficient. You need **{base_req} Ki** for this ascension. (Current: {ki})", ephemeral=True)

        view = BreakthroughView(ctx, user_id, self.get_db)
        embed = discord.Embed(title="⚔️ Realm Ascension Initiation", 
                              description=view.prompts[0]["text"], 
                              color=0x700000)
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
