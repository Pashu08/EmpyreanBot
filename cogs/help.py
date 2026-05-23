import discord
from discord.ext import commands
from utils.helpers import format_embed_color
from utils.db import get_bot_setting
import config

print("[DEBUG] help.py: Loading Help cog...")

# ==========================================
# HELP DROPDOWN MENU (No admin category)
# ==========================================
class HelpSelect(discord.ui.Select):
    def __init__(self, member_id):
        self.member_id = member_id

        options = [
            discord.SelectOption(label="Genesis & Basics", description="Start your journey & core stats.", emoji="🏁"),
            discord.SelectOption(label="Cultivation & Training", description="Ki, Mastery, and breakthroughs.", emoji="🌀"),
            discord.SelectOption(label="Combat & Warfare", description="Hunting and battle mechanics.", emoji="⚔️"),
            discord.SelectOption(label="Inventory & Shop", description="Manage items and visit the market.", emoji="🎒"),
            discord.SelectOption(label="Daily Actions & Recovery", description="Work, meditation, and rest.", emoji="🏮"),
        ]

        super().__init__(placeholder="Choose a category to study...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member_id:
            return await interaction.response.send_message(
                config.MSG_HELP_ALREADY_VIEWING,
                ephemeral=True
            )

        embed = discord.Embed(color=format_embed_color("main"))

        if self.values[0] == "Genesis & Basics":
            embed.title = "🏁 The Beginning"
            embed.description = (
                "**`!start`** — Begin your journey and choose a background.\n"
                "**`!stats`** (alias `!st`) — View your Rank, Ki, Mastery, and Meridian Health.\n"
                "**`!profile`** (alias `!prof`) — View detailed character sheet.\n"
                "**`!pstatus`** — View your professional rank and progress.\n"
                "**`!afk`** (alias `!away`) — Check your AFK gains.\n"
                "**`!pouch`** (alias `!money`, `!wealth`) — Check your Taels."
            )
        elif self.values[0] == "Cultivation & Training":
            embed.title = "🌀 Path of Power"
            embed.description = (
                "**`!observe`** — Meditate to gain Ki and Mastery.\n"
                "**`!comprehend`** — Deeply study your technique for massive Mastery.\n"
                "**`!pavilion`** (alias `!pav`) — Choose or view your active technique.\n"
                "**`!techniques`** (alias `!techs`) — List all available techniques.\n"
                "**`!reset_technique`** — Abandon your current technique (costs 500 Taels).\n"
                "**`!breakthrough`** (alias `!bt`) — Attempt to reach the next Major Realm.\n"
                "**`!breakthrough_status`** (alias `!btst`) — Check breakthrough progress and bonuses."
            )
        elif self.values[0] == "Combat & Warfare":
            embed.title = "⚔️ Martial Conflict"
            embed.description = (
                "**`!hunt`** (alias `!h`) — Hunt spirit beasts for rewards.\n"
                "**`!spar @user [bet]`** — Challenge another player to a spar.\n"
                "**`!huntleaderboard`** (alias `!hlb`) — View hunting leaderboards."
            )
        elif self.values[0] == "Inventory & Shop":
            embed.title = "🎒 Inventory & Shop"
            embed.description = (
                "**`!inventory`** (alias `!inv`) — View your items.\n"
                "**`!use <item>`** — Consume an item.\n"
                "**`!bazaar`** (alias `!bz`) — Browse the market.\n"
                "**`!buy <item> [qty]`** — Purchase an item.\n"
                "**`!sell <item> [qty]`** — Sell an item.\n"
                "**`!give @user <item> [qty]`** — Give an item to another player.\n"
                "**`!search <item>`** — Find which shop sells an item.\n"
                "**`!pouch`** (alias `!money`, `!wealth`) — Check your Taels."
            )
        elif self.values[0] == "Daily Actions & Recovery":
            embed.title = "🏮 Daily Actions & Recovery"
            embed.description = (
                "**`!work`** — Earn Taels.\n"
                "**`!recover`** — Meditate to restore Vitality and Ki.\n"
                "**`!cancel`** — Cancel active meditation.\n"
                "**`!meditate`** — Check next heartbeat.\n"
                "**`!focus`** — Convert Vitality to Ki.\n"
                "**`!rest`** — Instantly restore HP and Vitality.\n"
                "**`!toggle_dm`** — Enable/disable heartbeat DMs.\n"
                "**`!afk`** (alias `!away`) — Check your AFK gains."
            )

        embed.set_footer(text="The heavens watch every step you take.")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(member_id))

# ==========================================
# MAIN COG
# ==========================================
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if bot.get_command('help'):
            bot.remove_command('help')
        print("[DEBUG] Help cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_help", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Help"), ephemeral=True)
        return enabled

    @commands.hybrid_command(name="help", description="The complete manual for Empyrean Ascent.")
    async def help(self, ctx):
        """Displays the interactive manual."""
        print(f"[DEBUG] help.help: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return

        embed = discord.Embed(
            title="📜 The Path of the Bound: Complete Manual",
            description=(
                "Welcome to the world of Empyrean Ascent.\n\n"
                "Select a category below to begin your study.\n"
                "💡 **Tip:** Many commands have short aliases (e.g., `!st` for `!stats`).\n\n"
                "⚙️ **Admin commands** are available via `!divine` (admin only)."
            ),
            color=format_embed_color("main")
        )
        view = HelpView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
    print("[DEBUG] help.py: Setup complete")