import discord
from discord.ext import commands
from discord import app_commands

# --- V2 DROPDOWN MENU ---
class HelpSelect(discord.ui.Select):
    def __init__(self, member_id):
        self.member_id = member_id
        options = [
            discord.SelectOption(label="Genesis & Basics", description="Start your journey & core stats.", emoji="🏁"),
            discord.SelectOption(label="Cultivation & Training", description="Ki, Mastery, and breakthroughs.", emoji="🌀"),
            discord.SelectOption(label="Daily Actions", description="Working, meditating, and recovery.", emoji="⚒️"),
            discord.SelectOption(label="The Marketplace", description="Buying scrolls and items.", emoji="🏮"),
            discord.SelectOption(label="Professions", description="Path-specific career commands.", emoji="🎓")
        ]
        super().__init__(placeholder="Choose a category to study...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # --- EXCLUSIVE LOCK CHECK ---
        if interaction.user.id != self.member_id:
            return await interaction.response.send_message("❌ This manual is being studied by another. Open your own with `!help`.", ephemeral=True)

        embed = discord.Embed(color=0x700000)
        
        if self.values[0] == "Genesis & Basics":
            embed.title = "🏁 The Beginning"
            embed.description = (
                "**`!start`** — Begin your journey and choose a background.\n"
                "**`!stats`** — View your Rank, Ki, Mastery, and Items.\n"
                "**`!pstatus`** — View your professional rank and progress."
            )
        elif self.values[0] == "Cultivation & Training":
            embed.title = "🌀 Path of Power"
            embed.description = (
                "**`!observe`** — Meditate to gain Ki and Mastery (Costs Vitality).\n"
                "**`!pavilion`** — Visit the library to bind a new technique.\n"
                "**`!breakthrough`** — Attempt to reach the next Major Realm.\n"
                "**`!pchoose`** — Commit to a life-path profession (Permanent)."
            )
        elif self.values[0] == "Daily Actions":
            embed.title = "⚒️ Training & Recovery"
            embed.description = (
                "**`!work`** — Labor to earn Taels (Costs Vitality).\n"
                "**`!meditate`** — Check time until natural recovery.\n"
                "**`!actions`** — View list of available roleplay actions."
            )
        elif self.values[0] == "The Marketplace":
            embed.title = "🏮 The Great Bazaar"
            embed.description = (
                "**`!bazaar`** — Access the marketplace stalls.\n"
                "🔹 **Apothecary:** Pills for Ki and healing.\n"
                "🔹 **Scroll Merchant:** Manuals for techniques.\n"
                "🔹 **Provisioner:** Recovery items.\n"
                "🌑 **Shady Dealer:** Secret shop for Outcasts."
            )
        elif self.values[0] == "Professions":
            embed.title = "🎓 Career Commands"
            embed.description = (
                "**`!pchoose`** — Select: Alchemist, Blacksmith, Gatherer, Master, or Instructor.\n"
                "**`!pstatus`** — Monitor your professional XP and Rank."
            )

        embed.set_footer(text="The heavens watch every step you take.")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(member_id))

# --- THE COG ---
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if bot.get_command('help'):
            bot.remove_command('help')

    @commands.hybrid_command(name="help", description="The complete manual for Empyrean Ascent.")
    async def help(self, ctx):
        """Displays the interactive manual."""
        embed = discord.Embed(
            title="📜 The Path of the Bound: Complete Manual",
            description=(
                "Welcome to the world of Empyrean Ascent.\n\n"
                "This manual contains every technique and command known to mortals. "
                "Select a category below to begin your study."
            ),
            color=0x700000
        )
        # Passing the author ID to lock the view
        view = HelpView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
