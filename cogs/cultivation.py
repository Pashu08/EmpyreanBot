import discord
from discord.ext import commands
import sqlite3
import random
import asyncio

# --- BREAKTHROUGH UI ---
class BreakthroughView(discord.ui.View):
    def __init__(self, ctx, member_id, db_func):
        super().__init__(timeout=60)
        self.ctx = ctx
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

        # 50% chance of success for each button click
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
            # SUCCESS LOGIC
            new_rank = "Third-Rate Warrior"
            # Mutation Logic
            user_data = c.execute("SELECT item_id FROM users WHERE user_id=?", (self.member_id,)).fetchone()
            current_item = user_data[0]
            mutations = {"Torn Page": "Jade Scripture", "Black Coin": "Shadow Seal", "Glowing Fruit": "Verdant Bone"}
            new_item = mutations.get(current_item, current_item)

            c.execute("UPDATE users SET rank=?, item_id=?, ki=0, vitality=300, hp=300 WHERE user_id=?", 
                      (new_rank, new_item, self.member_id))
            
            result_embed = discord.Embed(title="🎊 BREAKTHROUGH SUCCESS", 
                                        description=f"You have ascended to **{new_rank}**!\nYour item has evolved into: **{new_item}**.", 
                                        color=0x00FF00)
        else:
            # FAILURE LOGIC
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

    @commands.command(name="breakthrough")
    async def breakthrough(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT ki, rank FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user: return await ctx.send("Start your journey first.")
        if user[0] < 100: return await ctx.send(f"❌ You need 100 Ki to attempt a breakthrough. (Current: {user[0]})")
        if "Third-Rate" in user[1]: return await ctx.send("You have already reached the peak of this stage.")

        view = BreakthroughView(ctx, ctx.author.id, self.get_db)
        embed = discord.Embed(title="⚔️ Breakthrough Initiation", 
                              description=view.prompts[0]["text"], 
                              color=0x700000)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
