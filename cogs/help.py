import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Removing the default help command to use our custom one
        bot.remove_command('help')

    @commands.command(name="help")
    async def help(self, ctx):
        """The Mortal's Guide to Ascension."""
        embed = discord.Embed(
            title="📜 The Path of the Bound: Manual",
            description="Welcome, seeker. Here are the techniques available to those who walk the path of cultivation.",
            color=0x2f3136
        )

        # Category: Genesis
        embed.add_field(
            name="🏁 Genesis",
            value="`!start <background>` - Begin your journey as a Laborer, Outcast, or Hermit.",
            inline=False
        )

        # Category: Cultivation
        embed.add_field(
            name="🌀 Cultivation",
            value=(
                "`!stats` - View your Rank, Ki, and Vital Statistics.\n"
                "`!breakthrough` - Attempt to open your meridians (Requires 100 Ki)."
            ),
            inline=False
        )

        # Category: Actions
        embed.add_field(
            name="⚒️ Daily Struggle",
            value=(
                "`!work` - Labor to earn Taels (Costs Vitality).\n"
                "`!observe` - Meditate to gain Ki (Costs Vitality)."
            ),
            inline=False
        )

        embed.set_footer(text="Type a command to begin. The heavens watch your progress.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
