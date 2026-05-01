import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import asyncio
import datetime

# --- NEW: ADVANCED PAVILION UI ---
class PavilionSelect(discord.ui.Select):
    def __init__(self, member_id):
        self.member_id = member_id
        options = [
            discord.SelectOption(label="Flowing Cloud Steps", description="Focus: Evasion & Agility", emoji="💨"),
            discord.SelectOption(label="Swift Wind Kick", description="Focus: Speed & Multi-hit", emoji="🦶"),
            discord.SelectOption(label="Golden Bell Shield", description="Focus: Damage Reduction", emoji="🔔"),
            discord.SelectOption(label="Vajra Guard Mantra", description="Focus: Vitality Regeneration", emoji="🧘")
        ]
        super().__init__(placeholder="Examine a scroll more closely...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member_id:
            return await interaction.response.send_message("❌ This enlightenment is not meant for you.", ephemeral=True)

        selection = self.values[0]
        view: PavilionView = self.view
        view.selected_tech = selection

        details = {
            "Flowing Cloud Steps": {
                "story": "The ink on this scroll drifts like mist. It depicts a master walking through a rainstorm without a single drop touching his robes.",
                "effect": "🔹 **Effect:** Increases **Dodge Chance by 15%**. You become a ghost on the battlefield.",
                "color": 0x3498db
            },
            "Swift Wind Kick": {
                "story": "The paper is warm to the touch. You see drawings of a warrior whose legs move so fast they create vacuum blades.",
                "effect": "🔹 **Effect:** Increases **Attack Speed**. Grants a chance to strike twice in one turn.",
                "color": 0xe67e22
            },
            "Golden Bell Shield": {
                "story": "This scroll is heavy, bound in iron. It describes the art of hardening Ki into an invisible bell of protection.",
                "effect": "🔹 **Effect:** Reduces **Incoming Damage by 20%**. Stand firm against any tide.",
                "color": 0xf1c40f
            },
            "Vajra Guard Mantra": {
                "story": "A soothing light radiates from the symbols. It teaches the secret of breathing in rhythm with the heavens to heal wounds.",
                "effect": "🔹 **Effect:** Restores **5% HP every turn** during combat. Your endurance is limitless.",
                "color": 0x2ecc71
            }
        }

        data = details[selection]
        embed = discord.Embed(
            title=f"📜 Inspecting: {selection}", 
            description=f"*{data['story']}*\n\n{data['effect']}", 
            color=data['color']
        )
        embed.set_footer(text="If this path calls to you, click 'Begin Training' below.")
        
        view.confirm_btn.disabled = False
        await interaction.response.edit_message(embed=embed, view=view)

class PavilionView(discord.ui.View):
    def __init__(self, ctx, member_id, db_func):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.member_id = member_id
        self.get_db = db_func
        self.selected_tech = None

        self.add_item(PavilionSelect(member_id))
        
        self.confirm_btn = discord.ui.Button(label="Begin Training", style=discord.ButtonStyle.success, disabled=True)
        self.confirm_btn.callback = self.confirm_selection
        self.add_item(self.confirm_btn)

    async def confirm_selection(self, interaction: discord.Interaction):
        conn = self.get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET active_tech = ?, mastery = 0.0 WHERE user_id = ?", (self.selected_tech, self.member_id))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✨ Path Bound", 
            description=f"You have committed your soul to the **{self.selected_tech}**.\n\n"
                        f"Your journey toward mastery begins now. Use `!observe` or `!comprehend` to train.",
            color=0x00FF00
        )
        await interaction.response.edit_message(embed=embed, view=None)

class Mechanics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Track active meditation and cooldowns
        self.meditating = set()
        self.cooldowns = {}
        self.heartbeat.start()

    def cog_unload(self):
        self.heartbeat.cancel()

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # BUFFED HEARTBEAT LOOP (Automatic Recovery)
    # ==========================================
    @tasks.loop(minutes=10.0)
    async def heartbeat(self):
        conn = self.get_db()
        c = conn.cursor()
        users = c.execute("SELECT user_id, hp, vitality, rank FROM users").fetchall()
        
        for user in users:
            u_id, current_hp, current_vit, rank = user
            # BUFFED RATES: Players can actually play now
            if "Second-Rate" in rank: regen = 100
            elif "Third-Rate" in rank: regen = 50
            else: regen = 25 # Mortal now gets 25% back every 10m
            
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
    # ACTIVE RECOVERY (Lotus Meditation)
    # ==========================================
    @commands.hybrid_command(name="recover", description="Active meditation: Restore 25 Vit in 60s.")
    async def recover(self, ctx):
        user_id = ctx.author.id
        now = datetime.datetime.now()

        # 1. Check Cooldown (5 Minutes)
        if user_id in self.cooldowns:
            if now < self.cooldowns[user_id]:
                diff = self.cooldowns[user_id] - now
                return await ctx.send(f"❌ Your soul is still stabilizing. Wait **{int(diff.total_seconds())}s** before meditating again.", ephemeral=True)

        if user_id in self.meditating:
            return await ctx.send("🧘 You are already in deep meditation.", ephemeral=True)

        self.meditating.add(user_id)
        # Lockout shared with bot for other cogs
        if not hasattr(self.bot, 'is_meditating'): self.bot.is_meditating = set()
        self.bot.is_meditating.add(user_id)

        await ctx.send("🧘 You enter a state of deep meditation. Your senses dull as your Ki stabilizes... (Wait: 60s)")
        
        await asyncio.sleep(60)
        
        # 2. Update Database
        conn = self.get_db()
        c = conn.cursor()
        # Cap logic: Find player rank to check limits
        res = c.execute("SELECT rank FROM users WHERE user_id = ?", (user_id,)).fetchone()
        caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 300, "Second-Rate Warrior": 600}
        limit = caps.get(res[0], 1000) if res else 100
        
        c.execute("UPDATE users SET vitality = MIN(vitality + 25, ?) WHERE user_id = ?", (limit, user_id))
        conn.commit()
        conn.close()

        # 3. Set Cooldown & Cleanup
        self.meditating.remove(user_id)
        self.bot.is_meditating.remove(user_id)
        self.cooldowns[user_id] = now + datetime.timedelta(minutes=5)
        
        await ctx.send(f"✨ {ctx.author.mention}, you open your eyes as refreshing energy flows through your meridians! (+25 Vitality)")

    # ==========================================
    # HYBRID COMMANDS (!pavilion)
    # ==========================================
    @commands.hybrid_command(name="pavilion")
    async def pavilion(self, ctx):
        # Meditating check
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send("❌ You cannot enter the Pavilion while in deep meditation!", ephemeral=True)

        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT rank, ki, active_tech, mastery FROM users WHERE user_id = ?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        rank, ki, active_tech, mastery = user
        if "Mortal" in rank and ki < 100:
            return await ctx.send("❌ The scrolls are sealed. You need **100 Ki** to understand these foundations.", ephemeral=True)

        if active_tech != "None":
            embed = discord.Embed(
                title="🏮 Pavilion: Current Focus",
                description=f"You are currently focusing on **{active_tech}**.\n"
                            f"**Current Mastery:** `{mastery}%` / 100%\n\n"
                            f"*To switch techniques, you must complete your current study or reset your progress.*",
                color=0x700000
            )
            return await ctx.send(embed=embed)

        view = PavilionView(ctx, ctx.author.id, self.get_db)
        embed = discord.Embed(
            title="🏮 Pavilion of Hidden Scrolls",
            description="The air is thick with the scent of old paper. Choose a scroll from the menu below to read its legend.",
            color=0x700000
        )
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
