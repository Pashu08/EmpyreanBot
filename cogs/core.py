import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

# --- THE ENHANCED START MENU ---
class StartMenu(discord.ui.View):
    def __init__(self, user_id, db_func):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.get_db = db_func

    async def handle_start(self, interaction, background, item, description):
        # --- EXCLUSIVE LOCK: Only the summoner can choose ---
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This destiny is not yours to claim.", ephemeral=True)

        conn = self.get_db()
        c = conn.cursor()
        
        user = c.execute("SELECT user_id FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()
        if user:
            conn.close()
            return await interaction.response.send_message("❌ You are already walking the path of cultivation.", ephemeral=True)

        # FIXED: Capture current timestamp to prevent instant AFK gain glitch
        now = datetime.datetime.now().isoformat()

        # Initializing with Mortal stats and the correct starting timestamp
        c.execute("""INSERT INTO users (user_id, background, rank, item_id, taels, ki, vitality, hp, stage, last_refresh) 
                     VALUES (?, ?, ?, ?, 0, 0, 100, 100, 'Initial', ?)""",
                  (interaction.user.id, background, "The Bound (Mortal)", item, now))
        conn.commit()
        conn.close()
        
        # Success Embed
        success_embed = discord.Embed(
            title="🌅 A New Legend Begins",
            description=(
                f"The heavens tremble as you step forward. You have chosen the path of the **{background}**.\n\n"
                f"**Initial Item:** `{item}`\n"
                f"**Current Status:** The Bound (Mortal)\n\n"
                "*Go forth and cultivate. Your ascent begins now.*"
            ),
            color=0x00FF00
        )
        await interaction.response.edit_message(content=None, embed=success_embed, view=None)
        self.stop()

    @discord.ui.button(label="Laborer", style=discord.ButtonStyle.green, emoji="⚒️")
    async def laborer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Laborer", "Torn Page", "One who finds wisdom in hard work.")

    @discord.ui.button(label="Outcast", style=discord.ButtonStyle.grey, emoji="🌑")
    async def outcast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Outcast", "Black Coin", "One who walks the shadows and forbidden markets.")

    @discord.ui.button(label="Hermit", style=discord.ButtonStyle.blurple, emoji="🌿")
    async def hermit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Hermit", "Glowing Fruit", "One who lives in harmony with natural spirits.")

# --- THE COG ---
class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="start", description="Begin your journey in the Murim world")
    async def start(self, ctx):
        """Opens the beautiful choice menu for new players."""
        user_id = ctx.author.id
        
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        conn.close()

        if user:
            return await ctx.send("❌ Your path is already set. Check your `!stats`.")

        # --- THE FIRST IMPRESSION EMBED ---
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
            color=0x700000
        )
        embed.set_footer(text="Your choice is permanent. Choose with wisdom.")
        
        view = StartMenu(user_id, self.get_db)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Core(bot))
