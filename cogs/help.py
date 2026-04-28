import discord
from discord.ext import commands
from discord import app_commands

# --- V2 DROPDOWN MENU ---
class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Genesis & Basics", description="How to start and view stats.", emoji="🏁"),
            discord.SelectOption(label="Cultivation", description="Ranks and breakthroughs.", emoji="🌀"),
            discord.SelectOption(label="Daily Struggle", description="Working and meditating.", emoji="⚒️")
        ]
        super().__init__(placeholder="Choose a path to study...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(color=0x2f3136)
        
        if self.values[0] == "Genesis & Basics":
            embed.title = "🏁 The Beginning"
            embed.description = (
                "**`/start`** - Begin your journey as a Laborer, Outcast, or Hermit.\n"
                "**`/stats`** - View your Rank, Ki, and Vital Statistics."
            )
        elif self.values[0] == "Cultivation":
            embed.title = "🌀 Path of Power"
            embed.description = (
                "**`/breakthrough`** - Attempt to reach the next rank.\n"
                "🔹 *Mortal → Third-Rate (100 Ki)*\n"
                "🔹 *Third-Rate → Second-Rate (300 Ki)*"
            )
        elif self.values[0] == "Daily Struggle":
            embed.title = "⚒️ Training & Labor"
            embed.description = (
                "**`/work`** - Labor to earn Taels (Costs Vitality).\n"
                "**`/observe`** - Meditate to gain Ki (Costs Vitality).\n"
                "**`/meditate`** - Check time until natural recovery."
            )

        embed.set_footer(text="The heavens watch your progress.")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(HelpSelect())

# --- THE COG ---
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Removing the default help command to use our custom one
        bot.remove_command('help')

    @commands.hybrid_command(name="help", description="The Mortal's Guide to Ascension")
    async def help(self, ctx):
        """Displays the interactive manual."""
        embed = discord.Embed(
            title="📜 The Path of the Bound: Manual",
            description="Welcome, seeker. Select a category from the menu below to study the techniques of this world.",
            color=0x2f3136
        )
        view = HelpView()
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
