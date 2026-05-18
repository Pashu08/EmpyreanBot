import discord
from discord.ext import commands
from utils.helpers import format_embed_color
from utils.db import get_bot_setting
import config

print("[DEBUG] help.py: Loading Help cog...")

# ==========================================
# HELP DROPDOWN MENU
# ==========================================
class HelpSelect(discord.ui.Select):
    def __init__(self, member_id, is_admin):
        self.member_id = member_id
        self.is_admin = is_admin

        options = [
            discord.SelectOption(label="Genesis & Basics", description="Start your journey & core stats.", emoji="🏁"),
            discord.SelectOption(label="Cultivation & Training", description="Ki, Mastery, and breakthroughs.", emoji="🌀"),
            discord.SelectOption(label="Combat & Warfare", description="Hunting and battle mechanics.", emoji="⚔️"),
            discord.SelectOption(label="Inventory & Shop", description="Manage items and visit the market.", emoji="🎒"),
            discord.SelectOption(label="Daily Actions & Recovery", description="Work, meditation, and rest.", emoji="🏮"),
        ]

        if is_admin:
            options.append(discord.SelectOption(label="⚙️ Admin Commands", description="Bot management and configuration.", emoji="🔧"))

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
                "**`!pstatus`** — View your professional rank and progress."
            )
        elif self.values[0] == "Cultivation & Training":
            embed.title = "🌀 Path of Power"
            embed.description = (
                "**`!observe`** — Meditate to gain Ki and Mastery.\n"
                "**`!comprehend`** — Deeply study your technique for massive Mastery.\n"
                "**`!pavilion`** (alias `!pav`) — Choose or view your active technique.\n"
                "**`!techniques`** (alias `!techs`) — List all available techniques.\n"
                "**`!reset_technique`** — Abandon your current technique (costs 500 Taels).\n"
                "**`!breakthrough`** — Attempt to reach the next Major Realm."
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
                "**`!search <item>`** — Find which shop sells an item."
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
                "**`!toggle_dm`** — Enable/disable heartbeat DMs."
            )
        elif self.values[0] == "⚙️ Admin Commands" and self.is_admin:
            embed.title = "🔧 Admin Commands"
            embed.description = (
                "**Player Management:**\n"
                "`!reset @user` `!setki` `!settaels` `!setmastery` `!setcombat`\n"
                "`!fixmeridians @user` `!refill @user`\n\n"
                "**Configuration:**\n"
                "`!toggle <feature>` `!set_cooldown` `!set_emoji` `!set_message`\n"
                "`!debug <on/off>` `!settings`\n\n"
                "**System:**\n"
                "`!sync` `!pulse` `!promote` `!demote`\n"
                "`!allow @user <perm>` `!deny @user <perm>` `!perms @user`\n"
                "`!ban @user <reason>` `!unban @user`"
            )

        embed.set_footer(text="The heavens watch every step you take.")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, member_id, is_admin):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(member_id, is_admin))

# ==========================================
# MAIN COG
# ==========================================
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if bot.get_command('help'):
            bot.remove_command('help')
        print("[DEBUG] Help cog initialized")

    async def _has_permission(self, user_id, permission):
        """Check if a user has a specific permission."""
        db = self.bot.db
        async with db.execute("SELECT 1 FROM admin_permissions WHERE user_id = ? AND permission = ?", (user_id, permission)) as cursor:
            return await cursor.fetchone() is not None

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

        is_admin = await self._has_permission(ctx.author.id, "system") or \
                   await self._has_permission(ctx.author.id, "config_manage") or \
                   await self._has_permission(ctx.author.id, "player_manage")

        embed = discord.Embed(
            title="📜 The Path of the Bound: Complete Manual",
            description=(
                "Welcome to the world of Empyrean Ascent.\n\n"
                "Select a category below to begin your study.\n"
                "💡 **Tip:** Many commands have short aliases (e.g., `!st` for `!stats`)."
            ),
            color=format_embed_color("main")
        )
        view = HelpView(ctx.author.id, is_admin)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
    print("[DEBUG] help.py: Setup complete")