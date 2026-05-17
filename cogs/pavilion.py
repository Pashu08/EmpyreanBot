import discord
from discord.ext import commands
from utils.helpers import format_embed_color
from utils.db import get_bot_setting, is_user_banned, get_user_stat, update_user_stat
from utils.constants import TECHNIQUES
import config

print("[DEBUG] pavilion.py: Loading Pavilion cog...")

class PavilionSelect(discord.ui.Select):
    def __init__(self, member_id, available_techs):
        self.member_id = member_id
        self.available_techs = available_techs
        options = []
        for tech_name in available_techs:
            tech_data = TECHNIQUES.get(tech_name, {})
            emoji = tech_data.get("emoji", "📜")
            options.append(
                discord.SelectOption(
                    label=tech_name,
                    description=tech_data.get("description", "A martial technique")[:50],
                    emoji=emoji
                )
            )
        super().__init__(placeholder="Examine a scroll more closely...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member_id:
            return await interaction.response.send_message("❌ This enlightenment is not meant for you.", ephemeral=True)

        selection = self.values[0]
        view: PavilionView = self.view
        view.selected_tech = selection

        tech_data = TECHNIQUES.get(selection, {})
        story = tech_data.get("story", "The scroll is ancient and mysterious.")
        effect_text = tech_data.get("effect_text", "Unknown effect.")
        color = tech_data.get("color", format_embed_color("main"))

        embed = discord.Embed(
            title=f"📜 Inspecting: {selection}",
            description=f"*{story}*\n\n🔹 **Effect:** {effect_text}",
            color=color
        )
        embed.set_footer(text="If this path calls to you, click 'Begin Training' below.")

        view.confirm_btn.disabled = False
        await interaction.response.edit_message(embed=embed, view=view)

class PavilionView(discord.ui.View):
    def __init__(self, ctx, member_id, bot, available_techs):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.member_id = member_id
        self.bot = bot
        self.selected_tech = None

        self.add_item(PavilionSelect(member_id, available_techs))

        self.confirm_btn = discord.ui.Button(label="Begin Training", style=discord.ButtonStyle.success, disabled=True)
        self.confirm_btn.callback = self.confirm_selection
        self.add_item(self.confirm_btn)

    async def confirm_selection(self, interaction: discord.Interaction):
        if not self.selected_tech:
            return await interaction.response.send_message("❌ Please select a technique first.", ephemeral=True)

        db = self.bot.db
        await db.execute(
            "UPDATE users SET active_tech = ?, mastery = 0.0 WHERE user_id = ?",
            (self.selected_tech, self.member_id)
        )
        await db.commit()

        # Check for hidden technique unlocks
        hidden_unlocked = await self._check_hidden_techniques(interaction.user.id)

        embed = discord.Embed(
            title="✨ Path Bound",
            description=f"You have committed your soul to the **{self.selected_tech}**.\n\nYour journey begins. Use `!observe` or `!comprehend` to train.",
            color=format_embed_color("win")
        )
        if hidden_unlocked:
            embed.add_field(name="🌟 Hidden Insight", value=hidden_unlocked, inline=False)

        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def _check_hidden_techniques(self, user_id):
        """Check if user has unlocked any hidden techniques based on mastered techniques."""
        # This is a placeholder – you will implement actual hidden technique logic later.
        # For now, it checks a hypothetical 'hidden_techs_unlocked' column.
        db = self.bot.db
        async with db.execute("SELECT hidden_techs_unlocked FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return f"You have unlocked: {row[0]}"
        return None

class Pavilion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Pavilion cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_pavilion", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Pavilion"), ephemeral=True)
        return enabled

    @commands.hybrid_command(name="pavilion", aliases=["pav"], description="Visit the Pavilion of Hidden Scrolls.")
    async def pavilion(self, ctx):
        print(f"[DEBUG] pavilion.pavilion: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send(config.MSG_ALREADY_MEDITATING, ephemeral=True)

        db = self.bot.db
        async with db.execute("SELECT rank, ki, active_tech, mastery FROM users WHERE user_id = ?", (ctx.author.id,)) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        rank, ki, active_tech, mastery = user

        if "Mortal" in rank and ki < 100:
            return await ctx.send("❌ The scrolls are sealed. You need **100 Ki** to understand these foundations.", ephemeral=True)

        if active_tech != "None":
            embed = discord.Embed(
                title="🏮 Pavilion: Current Focus",
                description=f"You are focusing on **{active_tech}**.\n**Mastery:** `{mastery}%` / 100%\n\nTo switch, use `!reset_technique` (costs 500 Taels).",
                color=format_embed_color("main")
            )
            return await ctx.send(embed=embed)

        # Get available techniques (all from constants for now – hidden ones filtered later)
        available_techs = list(TECHNIQUES.keys())

        view = PavilionView(ctx, ctx.author.id, self.bot, available_techs)
        embed = discord.Embed(
            title="🏮 Pavilion of Hidden Scrolls",
            description="Choose a scroll from the menu below.",
            color=format_embed_color("main")
        )
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="reset_technique", aliases=["resettech"], description="Abandon your current technique and start a new path (costs 500 Taels).")
    async def reset_technique(self, ctx):
        print(f"[DEBUG] pavilion.reset_technique: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        async with db.execute("SELECT active_tech, mastery, taels FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        active_tech, mastery, taels = user

        if active_tech == "None":
            return await ctx.send("❌ You are not currently focusing on any technique.", ephemeral=True)

        RESET_COST = 500
        if taels < RESET_COST:
            return await ctx.send(f"❌ You need **{RESET_COST} Taels** to reset your technique (you have {taels}).", ephemeral=True)

        # Confirm with user
        view = discord.ui.View(timeout=30)
        confirm_btn = discord.ui.Button(label="✅ Confirm (500 Taels)", style=discord.ButtonStyle.danger)
        cancel_btn = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.secondary)

        async def confirm_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ Not your command.", ephemeral=True)

            # Deduct Taels and reset technique
            new_taels = taels - RESET_COST
            await db.execute("UPDATE users SET active_tech = 'None', mastery = 0.0, taels = ? WHERE user_id = ?", (new_taels, user_id))
            await db.commit()

            embed = discord.Embed(
                title="🔄 Technique Reset",
                description=f"You have abandoned **{active_tech}** (lost {mastery}% mastery).\n{RESET_COST} Taels were deducted.\n\nYou may now choose a new path with `!pavilion`.",
                color=format_embed_color("gold")
            )
            await interaction.response.edit_message(content=None, embed=embed, view=None)
            view.stop()

        async def cancel_callback(interaction):
            if interaction.user.id != user_id:
                return await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            await interaction.response.edit_message(content="❌ Technique reset cancelled.", view=None)
            view.stop()

        confirm_btn.callback = confirm_callback
        cancel_btn.callback = cancel_callback
        view.add_item(confirm_btn)
        view.add_item(cancel_btn)

        embed = discord.Embed(
            title="⚠️ Confirm Technique Reset",
            description=f"Are you sure you want to abandon **{active_tech}**?\n\nYou will lose **{mastery}% mastery** and **{RESET_COST} Taels**.",
            color=format_embed_color("lose")
        )
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="techniques", aliases=["techs"], description="List all available techniques.")
    async def list_techniques(self, ctx):
        print(f"[DEBUG] pavilion.list_techniques: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        embed = discord.Embed(
            title="📚 Martial Techniques",
            description="These are the techniques you can learn at the Pavilion.",
            color=format_embed_color("teal")
        )

        for tech_name, tech_data in TECHNIQUES.items():
            effect = tech_data.get("effect_text", "Unknown effect")
            embed.add_field(
                name=f"{tech_data.get('emoji', '📜')} {tech_name}",
                value=f"{tech_data.get('description', '')}\n*{effect}*",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pavilion(bot))
    print("[DEBUG] pavilion.py: Setup complete")