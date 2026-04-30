import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # HYBRID COMMAND: !work or /work
    # ==========================================
    @commands.hybrid_command(name="work", description="Perform manual labor for Taels")
    @app_commands.checks.cooldown(1, 5.0)
    async def work(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user_id = ctx.author.id
        
        user = c.execute("SELECT vitality, taels, rank, background, mastery, active_tech FROM users WHERE user_id=?", (user_id,)).fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)
        
        vit, taels, rank, bg, mastery, tech = user
        
        if "Second-Rate" in rank: max_vit = 600
        elif "Third-Rate" in rank: max_vit = 300
        else: max_vit = 100

        if vit < 10:
            return await ctx.send(f"❌ Your body is too exhausted. ({vit}/{max_vit})", ephemeral=True)

        gain = random.randint(5, 15)
        new_vit = max(0, vit - 10)
        new_taels = taels + gain
        
        mastery_msg = ""
        if bg == "Laborer" and tech != "None" and mastery < 100:
            if random.random() < 0.10:
                mastery_gain = 0.5
                new_mastery = min(100.0, mastery + mastery_gain)
                c.execute("UPDATE users SET mastery=? WHERE user_id=?", (new_mastery, user_id))
                mastery_msg = f"\n✨ **Laborer's Insight:** Your hard work refined your {tech}! (+0.5% Mastery)"

        c.execute("UPDATE users SET vitality=?, taels=? WHERE user_id=?", (new_vit, new_taels, user_id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="⚒️ Manual Labor", color=0x700000)
        embed.description = f"You spent hours performing grueling tasks for the local merchants.{mastery_msg}"
        embed.add_field(name="Gained", value=f"💰 **+{gain}** Taels", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        embed.set_footer(text=f"Current Total: {new_taels} Taels")
        
        await ctx.send(embed=embed)

    # ==========================================
    # HYBRID COMMAND: !observe or /observe
    # ==========================================
    @commands.hybrid_command(name="observe", description="Refine your Ki through meditation")
    @app_commands.checks.cooldown(1, 5.0)
    async def observe(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user_id = ctx.author.id
        
        # Added mastery and active_tech to selection
        user = c.execute("SELECT vitality, ki, rank, mastery, active_tech FROM users WHERE user_id=?", (user_id,)).fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        vit, ki, rank, mastery, tech = user
        
        if "Second-Rate" in rank: max_vit, ki_cap = 600, 3000
        elif "Third-Rate" in rank: max_vit, ki_cap = 300, 1000
        else: max_vit, ki_cap = 100, 100

        if vit < 10:
            return await ctx.send(f"❌ Your mind is too clouded by fatigue. ({vit}/{max_vit})", ephemeral=True)

        ki_gain = random.randint(3, 8)
        new_vit = max(0, vit - 10)
        new_ki = min(ki_cap, ki + ki_gain) 

        # --- MASTERY GAIN IN MEDITATION ---
        mastery_msg = ""
        new_mastery = mastery
        if tech != "None" and mastery < 100:
            m_gain = round(random.uniform(0.5, 1.5), 2)
            new_mastery = min(100.0, mastery + m_gain)
            mastery_msg = f"\n📖 **Mastery:** +{m_gain}%"

        c.execute("UPDATE users SET vitality=?, ki=?, mastery=? WHERE user_id=?", (new_vit, new_ki, new_mastery, user_id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="👁️ Deep Observation", color=0x00AABB)
        embed.description = f"You sat in silence, watching the flow of the world.{mastery_msg}"
        embed.add_field(name="Ki Refined", value=f"✨ **+{ki_gain}** Ki", inline=True)
        embed.add_field(name="Vitality Left", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        embed.set_footer(text=f"Total Mastery: {new_mastery}%")

        await ctx.send(embed=embed)

    # ==========================================
    # HYBRID COMMAND: !comprehend
    # ==========================================
    @commands.hybrid_command(name="comprehend", description="Deeply study your active technique for massive Mastery.")
    @app_commands.checks.cooldown(1, 1800.0) # 30 Minute Cooldown
    async def comprehend(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user_id = ctx.author.id
        
        user = c.execute("SELECT vitality, active_tech, mastery, rank FROM users WHERE user_id=?", (user_id,)).fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        vit, tech, mastery, rank = user
        
        if tech == "None" or tech == "None":
            return await ctx.send("❌ You have no technique to comprehend. Visit the `!pavilion`.", ephemeral=True)

        if vit < 40:
            return await ctx.send(f"❌ Your mind is too exhausted for deep thought. (Need 40 Vit, have {vit})", ephemeral=True)

        # High Mastery Gain: 5% to 10%
        gain = round(random.uniform(5.0, 10.0), 2)
        new_vit = max(0, vit - 40)
        new_mastery = min(100.0, mastery + gain)

        c.execute("UPDATE users SET vitality=?, mastery=? WHERE user_id=?", (new_vit, new_mastery, user_id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="🧠 Moment of Enlightenment", color=0xFFD700)
        embed.description = f"You closed your eyes and replayed the forms of **{tech}** in your mind."
        embed.add_field(name="Mastery Gained", value=f"📖 **+{gain}%**", inline=True)
        embed.add_field(name="Total Mastery", value=f"📊 **{new_mastery}%**/100%", inline=True)
        embed.set_footer(text=f"Vitality: -40 | Remaining: {new_vit}")

        await ctx.send(embed=embed)

    # ==========================================
    # COOLDOWN ERROR HANDLER
    # ==========================================
    @work.error
    @observe.error
    @comprehend.error
    async def action_error(self, ctx, error):
        if isinstance(error, (commands.CommandOnCooldown, app_commands.CommandOnCooldown)):
            await ctx.send(f"⏳ **Focus your breathing.** Wait {error.retry_after:.1f}s.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Actions(bot))
