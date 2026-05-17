import discord
from discord.ext import commands
import datetime
from utils.helpers import format_embed_color
from utils.db import get_bot_setting, is_user_banned, get_user_stat, update_user_stat
from utils.constants import BACKGROUNDS, ITEM_MUTATIONS
import config

print("[DEBUG] core.py: Loading Core cog...")

# ==========================================
# START MENU (Background selection)
# ==========================================
class StartMenu(discord.ui.View):
    def __init__(self, user_id, bot):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bot = bot

    async def handle_start(self, interaction, background_name):
        """Create a new character with the chosen background."""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This destiny is not yours to claim.", ephemeral=True)

        db = self.bot.db
        # Check if user already exists (async)
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (interaction.user.id,)) as cursor:
            existing = await cursor.fetchone()
        if existing:
            return await interaction.response.send_message(config.MSG_ALREADY_REGISTERED, ephemeral=True)

        # Get background data from constants
        bg_data = BACKGROUNDS.get(background_name, {})
        item_name = bg_data.get("item", "Torn Page")
        # Check if item mutates (not needed at start, but for consistency)
        # Starting stats from config
        now = datetime.datetime.now().isoformat()

        await db.execute(
            """INSERT INTO users (
                user_id, background, rank, item_id, taels, ki, vitality, hp, stage, last_refresh
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                interaction.user.id,
                background_name,
                "The Bound (Mortal)",
                item_name,
                0,  # taels
                0,  # ki
                config.START_VITALITY,
                config.START_HP,
                "Initial",
                now
            )
        )
        await db.commit()

        # Success embed
        success_embed = discord.Embed(
            title="🌅 A New Legend Begins",
            description=(
                f"The heavens tremble as you step forward. You have chosen the path of the **{background_name}**.\n\n"
                f"**Initial Item:** `{item_name}`\n"
                f"**Current Status:** The Bound (Mortal)\n\n"
                "*Go forth and cultivate. Your ascent begins now.*"
            ),
            color=format_embed_color("win")
        )
        await interaction.response.edit_message(content=None, embed=success_embed, view=None)

        # Send tutorial popup (feature #6)
        await self._send_tutorial(interaction.user)
        self.stop()

    async def _send_tutorial(self, user):
        """Send a tutorial popup to the new player."""
        embed = discord.Embed(
            title="📜 Your Journey Begins",
            description=(
                "Welcome to **Murim: Empyrean Ascent**!\n\n"
                "Here are a few commands to get you started:\n\n"
                "**💰 Earn Resources**\n"
                "• `!work` – Perform labor to earn Taels (costs Vitality)\n"
                "• `!observe` – Meditate to refine Ki and gain Mastery\n\n"
                "**📈 Grow Stronger**\n"
                "• `!comprehend` – Deeply study your technique for major Mastery gains\n"
                "• `!stats` – View your cultivation progress\n\n"
                "**🛒 Explore**\n"
                "• `!pavilion` – Choose a martial technique to learn\n"
                "• `!bazaar` – Buy items to aid your journey\n\n"
                "**⚔️ Fight**\n"
                "• `!hunt` – Hunt spirit beasts for rewards\n"
                "• `!spar @user` – Challenge another player to a friendly duel\n\n"
                "For a full list of commands, type `!help`.\n\n"
                "*The path to the peak is long. Take your first step.*"
            ),
            color=format_embed_color("teal")
        )
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            # If DMs are closed, send in the channel (ephemeral)
            pass  # The start command is already in a channel, but we can't send ephemeral from here easily

    @discord.ui.button(label="Laborer", style=discord.ButtonStyle.green, emoji="⚒️")
    async def laborer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Laborer")

    @discord.ui.button(label="Outcast", style=discord.ButtonStyle.grey, emoji="🌑")
    async def outcast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Outcast")

    @discord.ui.button(label="Hermit", style=discord.ButtonStyle.blurple, emoji="🌿")
    async def hermit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Hermit")

# ==========================================
# MAIN COG
# ==========================================
class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Core cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_core", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Character Creation"), ephemeral=True)
        return enabled

    @commands.hybrid_command(name="start", description="Begin your journey in the Murim world")
    async def start(self, ctx):
        """Opens the background selection menu for new players."""
        print(f"[DEBUG] core.start: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        # Check if user already exists
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            existing = await cursor.fetchone()
        if existing:
            return await ctx.send(config.MSG_ALREADY_REGISTERED, ephemeral=True)

        # Build the background selection embed
        embed = discord.Embed(
            title="🏮 Murim: Empyrean Ascent 🏮",
            description=(
                "Welcome, seeker. The path to immortality is paved with blood, ki, and resolve. "
                "Before you take your first step, you must choose your origin.\n\n"
                "**⚒️ Laborer**\n*Used to hardship. Gains Taels easily and has a knack for technique mastery.*\n\n"
                "**🌑 Outcast**\n*Shunned by society. Gains access to the Underworld Bazaar and forbidden goods.*\n\n"
                "**🌿 Hermit**\n*A soul of nature. Regenerates Vitality and HP faster than any other.*\n\n"
                "**Select your background below to begin.**"
            ),
            color=format_embed_color("main")
        )
        embed.set_footer(text="Your choice is permanent. Choose with wisdom.")

        view = StartMenu(user_id, self.bot)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Core(bot))
    print("[DEBUG] core.py: Setup complete")