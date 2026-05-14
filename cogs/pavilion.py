import discord
from discord.ext import commands

# ==========================================
# PAVILION UI (copied from mechanics.py)
# ==========================================
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
                "story": "The ink on this scroll drifts like mist...",
                "effect": "🔹 **Effect:** Increases **Dodge Chance by 15%**.",
                "color": 0x3498db
            },
            "Swift Wind Kick": {
                "story": "The paper is warm to the touch...",
                "effect": "🔹 **Effect:** Increases **Attack Speed**. Grants a chance to strike twice.",
                "color": 0xe67e22
            },
            "Golden Bell Shield": {
                "story": "This scroll is heavy, bound in iron...",
                "effect": "🔹 **Effect:** Reduces **Incoming Damage by 20%**.",
                "color": 0xf1c40f
            },
            "Vajra Guard Mantra": {
                "story": "A soothing light radiates from the symbols...",
                "effect": "🔹 **Effect:** Restores **5% HP every turn** during combat.",
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
    def __init__(self, ctx, member_id, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.member_id = member_id
        self.bot = bot
        self.selected_tech = None

        self.add_item(PavilionSelect(member_id))

        self.confirm_btn = discord.ui.Button(label="Begin Training", style=discord.ButtonStyle.success, disabled=True)
        self.confirm_btn.callback = self.confirm_selection
        self.add_item(self.confirm_btn)

    async def confirm_selection(self, interaction: discord.Interaction):
        db = self.bot.db
        await db.execute(
            "UPDATE users SET active_tech = ?, mastery = 0.0 WHERE user_id = ?",
            (self.selected_tech, self.member_id)
        )
        await db.commit()

        embed = discord.Embed(
            title="✨ Path Bound",
            description=f"You have committed your soul to the **{self.selected_tech}**.\n\nYour journey begins. Use `!observe` or `!comprehend` to train.",
            color=0x00FF00
        )
        await interaction.response.edit_message(embed=embed, view=None)

class Pavilion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="pavilion")
    async def pavilion(self, ctx):
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send("❌ You cannot enter the Pavilion while in deep meditation!", ephemeral=True)

        db = self.bot.db
        async with db.execute("SELECT rank, ki, active_tech, mastery FROM users WHERE user_id = ?", (ctx.author.id,)) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        rank, ki, active_tech, mastery = user
        if "Mortal" in rank and ki < 100:
            return await ctx.send("❌ The scrolls are sealed. You need **100 Ki** to understand these foundations.", ephemeral=True)

        if active_tech != "None":
            embed = discord.Embed(
                title="🏮 Pavilion: Current Focus",
                description=f"You are focusing on **{active_tech}**.\n**Mastery:** `{mastery}%` / 100%\n\nTo switch, you must complete your current study.",
                color=0x700000
            )
            return await ctx.send(embed=embed)

        view = PavilionView(ctx, ctx.author.id, self.bot)
        embed = discord.Embed(
            title="🏮 Pavilion of Hidden Scrolls",
            description="Choose a scroll from the menu below.",
            color=0x700000
        )
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Pavilion(bot))