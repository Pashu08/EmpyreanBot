import discord
from discord.ext import commands
from utils.helpers import format_embed_color
from utils.db import get_bot_setting, has_permission
import config

print("[DEBUG] help.py: Loading Help cog...")

# ==========================================
# HELP DROPDOWN MENU
# ==========================================
class HelpSelect(discord.ui.Select):
    def __init__(self, member_id, is_admin):
        self.member_id = member_id
        self.is_admin = is_admin

        # Base options for all players
        options = [
            discord.SelectOption(label="Genesis & Basics", description="Start your journey & core stats.", emoji="🏁"),
            discord.SelectOption(label="Cultivation & Training", description="Ki, Mastery, and breakthroughs.", emoji="🌀"),
            discord.SelectOption(label="Combat & Warfare", description="Hunting and battle mechanics.", emoji="⚔️"),
            discord.SelectOption(label="Inventory & Shop", description="Manage items and visit the market.", emoji="🎒"),
            discord.SelectOption(label="Daily Actions & Recovery", description="Work, meditation, and rest.", emoji="🏮"),
        ]

        # Add admin category if user has any admin permission
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
                "**`!profile`** (alias `!prof`) — View detailed character sheet (daily bonuses, milestones, etc.).\n"
                "**`!pstatus`** — View your professional rank and progress."
            )
        elif self.values[0] == "Cultivation & Training":
            embed.title = "🌀 Path of Power"
            embed.description = (
                "**`!observe`** — Meditate to gain Ki and a small bit of Mastery.\n"
                "**`!comprehend`** — Deeply study your technique for massive Mastery (30 min cooldown).\n"
                "**`!pavilion`** (alias `!pav`) — Visit the library to choose or view your active technique.\n"
                "**`!techniques`** (alias `!techs`) — List all available martial techniques.\n"
                "**`!reset_technique`** (alias `!resettech`) — Abandon your current technique (costs 500 Taels).\n"
                "**`!breakthrough`** — Attempt to reach the next Major Realm (requires Peak stage and enough Ki)."
            )
        elif self.values[0] == "Combat & Warfare":
            embed.title = "⚔️ Martial Conflict"
            embed.description = (
                "**`!hunt`** (alias `!h`) — Track down spirit beasts for Taels and Combat Mastery.\n"
                "🔹 **Strike:** Basic attack (no Ki cost).\n"
                "🔹 **Technique:** Use your bound scroll skill (costs Ki).\n"
                "**`!spar @user [bet]`** — Challenge another player to a friendly spar. Optional Taels bet.\n"
                "**`!huntleaderboard`** (alias `!hlb`) — View hunting leaderboards.\n"
                "⚠️ **Note:** Defeat results in a 10% Taels loss and Damaged Meridians."
            )
        elif self.values[0] == "Inventory & Shop":
            embed.title = "🎒 Inventory & Shop"
            embed.description = (
                "**`!inventory`** (alias `!inv`) — View your Taels and all stored items.\n"
                "**`!use <item_name>`** — Consume a pill, soup, or elixir from your bag.\n"
                "**`!bazaar`** (alias `!bz`) — Browse available items in the market.\n"
                "**`!buy <item> [quantity]`** — Purchase an item from the shop.\n"
                "**`!sell <item> [quantity]`** — Sell an item for half its price.\n"
                "**`!give @user <item> [quantity]`** — Give an item to another player (requires Third‑Rate Warrior).\n"
                "**`!search <item>`** — Find which shop sells an item.\n\n"
                "🔹 *Example: `!buy \"Spirit Gathering Dan\" 2`*"
            )
        elif self.values[0] == "Daily Actions & Recovery":
            embed.title = "🏮 Daily Actions & Recovery"
            embed.description = (
                "**`!work`** — Labor to earn Taels (costs Vitality).\n"
                "**`!recover`** — Enter Deep Meditation to restore Vitality and Ki (60s wait, 5 min cooldown).\n"
                "**`!cancel`** — Cancel active meditation (early cancellation penalty applies).\n"
                "**`!meditate`** — Check time until natural HP/Vitality recovery.\n"
                "**`!focus`** — Convert 10 Vitality into 5 Ki (5 min cooldown).\n"
                "**`!rest`** — Instantly restore 10 HP and 10 Vitality (1 hour cooldown).\n"
                "**`!toggle_dm`** — Enable/disable heartbeat recovery DMs."
            )
        elif self.values[0] == "⚙️ Admin Commands" and self.is_admin:
            embed.title = "🔧 Admin Commands"
            embed.description = (
                "**Player Management:**\n"
                "`!reset @user` — Erase a player\n"
                "`!setki <num> @user` — Set Ki levels\n"
                "`!settaels <num> @user` — Set Taels amount\n"
                "`!setmastery <num> @user` — Set Technique Mastery\n"
                "`!setcombat <num> @user` — Set Combat Mastery\n"
                "`!fixmeridians @user` — Instant heal meridian damage\n"
                "`!refill @user` — Full HP/Vitality restoration\n\n"
                "**Configuration:**\n"
                "`!toggle <feature>` — Turn features on/off (pvp, combat, actions, etc.)\n"
                "`!set_cooldown <cmd> <sec>` — Change command cooldown\n"
                "`!set_emoji <name> <emoji>` — Change bot emojis\n"
                "`!set_message <key> <text>` — Change bot messages\n"
                "`!debug <on/off>` — Toggle debug mode\n"
                "`!settings` — View all current settings\n\n"
                "**System:**\n"
                "`!sync` — Register slash commands\n"
                "`!pulse` — Force recovery heartbeat\n"
                "`!promote @user` — Grant temporary god powers\n"
                "`!demote @user` — Strip god powers\n"
                "`!allow @user <perm>` — Grant permissions (player_manage, config_manage, system)\n"
                "`!deny @user <perm>` — Remove permissions\n"
                "`!perms @user` — View user permissions\n"
                "`!ban @user <reason>` — Ban a user from the bot\n"
                "`!unban @user` — Unban a user"
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
        # Remove default help to use our custom Murim version
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

        # Check if user has any admin permission (for admin category)
        is_admin = await has_permission(self.bot, ctx.author.id, "system") or \
                   await has_permission(self.bot, ctx.author.id, "config_manage") or \
                   await has_permission(self.bot, ctx.author.id, "player_manage") or \
                   ctx.author.id in self.bot.owner_ids if hasattr(self.bot, 'owner_ids') else False

        embed = discord.Embed(
            title="📜 The Path of the Bound: Complete Manual",
            description=(
                "Welcome to the world of Empyrean Ascent.\n\n"
                "This manual contains every technique and command known to mortals. "
                "Select a category below to begin your study.\n\n"
                "💡 **Tip:** Many commands have short aliases (e.g., `!st` for `!stats`)."
            ),
            color=format_embed_color("main")
        )
        view = HelpView(ctx.author.id, is_admin)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
    print("[DEBUG] help.py: Setup complete")