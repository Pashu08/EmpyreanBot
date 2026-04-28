import discord
from discord.ext import commands
from discord import app_commands  # Added for V2
import sqlite3
import random
import asyncio

# --- BREAKTHROUGH UI ---
class BreakthroughView(discord.ui.View):
    def __init__(self, interaction, member_id, db_func): # Changed ctx to interaction for V2
        super().__init__(timeout=60)
        self.interaction = interaction
        self.member_id = member_id
        self.get_db = db_func
        self.stage = 1
        self.success_count = 0
        
        # Define the story prompts
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
            # SUCCESS LOGIC - DETERMINING NEXT RANK AND CAP
            user_data = c.execute("SELECT rank, item_id FROM users WHERE user_id=?", (self.member_id,)).fetchone()
            current_rank, current_item = user_data

            if "Mortal" in current_rank:
                new_rank = "Third-Rate Warrior"
                new_cap = 300
            else:
                new_rank = "Second-Rate Warrior"
                new_cap = 600

            # Mutation Logic
            mutations = {"Torn Page": "Jade Scripture", "Black Coin": "Shadow Seal", "Glowing Fruit": "Verdant Bone"}
            new_item = mutations.get(current_item, current_item)

            c.execute("UPDATE users SET rank=?, item_id=?, ki=0, vitality=?, hp=? WHERE user_id=?", 
                      (new_rank, new_item, new_cap, new_cap, self.member_id))
            
            result_embed = discord.Embed(title="🎊 BREAKTHROUGH SUCCESS", 
                                        description=f"You have ascended to **{new_rank}**!\nYour item has evolved into: **{new_item}**.\nYour limits have expanded to **{new_cap}**!", 
                                        color=0x00FF00)
        else:
            c.execute("UPDATE users SET ki = MAX(0, ki - 70) WHERE user_id=?", (self.member_id,))
            result_embed = discord.Embed(title="💀 BREAKTHROUGH FAILED", 
                                        description="The energy backfired. Your meridians are damaged and you lost 70 Ki.", 
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

    # Hybrid Support: Both !breakthrough and /breakthrough
    @commands.command(name="breakthrough")
    @app_commands.command(name="breakthrough", description="Attempt to reach a higher cultivation rank")
    async def breakthrough(self, ctx_or_interaction):
        # Handle both Message and Interaction
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        user_id = ctx_or_interaction.user.id if is_interaction else ctx_or_interaction.author.id
        
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT ki, rank FROM users WHERE user_id=?", (user_id,)).fetchone()
        conn.close()

        if not user: 
            msg = "Start your journey first."
            return await ctx_or_interaction.response.send_message(msg, ephemeral=True) if is_interaction else await ctx_or_interaction.send(msg)
        
        ki, rank = user[0], user[1]

        # Dynamic Requirement Check
        if "Mortal" in rank:
            if ki < 100:
                msg = f"❌ You need 100 Ki to reach Third-Rate. (Current: {ki})"
                return await ctx_or_interaction.response.send_message(msg, ephemeral=True) if is_interaction else await ctx_or_interaction.send(msg)
        elif "Third-Rate" in rank:
            if ki < 300:
                msg = f"❌ You need 300 Ki to reach Second-Rate. (Current: {ki})"
                return await ctx_or_interaction.response.send_message(msg, ephemeral=True) if is_interaction else await ctx_or_interaction.send(msg)
        else:
            msg = "You have reached the peak."
            return await ctx_or_interaction.response.send_message(msg, ephemeral=True) if is_interaction else await ctx_or_interaction.send(msg)

        view = BreakthroughView(ctx_or_interaction, user_id, self.get_db)
        embed = discord.Embed(title="⚔️ Breakthrough Initiation", 
                              description=view.prompts[0]["text"], 
                              color=0x700000)
        
        if is_interaction:
            await ctx_or_interaction.response.send_message(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
