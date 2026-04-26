import discord
from discord.ext import commands
import sqlite3

# --- THE BUTTON MENU ---
class StartMenu(discord.ui.View):
    def __init__(self, ctx, db_func):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.get_db = db_func

    async def handle_start(self, interaction, background, item):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("This isn't your destiny.", ephemeral=True)

        conn = self.get_db()
        c = conn.cursor()
        
        # Check if they exist again just to be safe
        user = c.execute("SELECT user_id FROM users WHERE user_id=?", (interaction.user.id,)).fetchone()
        if user:
            conn.close()
            return await interaction.response.send_message("❌ You are already on a path.", ephemeral=True)

        c.execute("INSERT INTO users (user_id, background, rank, item_id, taels, ki, vitality, hp) VALUES (?, ?, ?, ?, 0, 0, 100, 100)",
                  (interaction.user.id, background, "The Bound (Mortal)", item))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"✅ Journey started as **{background}**! You received: **{item}**.")
        self.stop() # Close the menu

    @discord.ui.button(label="Laborer", style=discord.ButtonStyle.green, emoji="⚒️")
    async def laborer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Laborer", "Torn Page")

    @discord.ui.button(label="Outcast", style=discord.ButtonStyle.grey, emoji="🌑")
    async def outcast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Outcast", "Black Coin")

    @discord.ui.button(label="Hermit", style=discord.ButtonStyle.blurple, emoji="🌿")
    async def hermit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_start(interaction, "Hermit", "Glowing Fruit")

# --- THE COG ---
class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.command(name="start")
    async def start(self, ctx):
        """Opens the choice menu for new players."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT user_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        conn.close()

        if user:
            return await ctx.send("❌ Your path is already set. Check your `!stats`.")

        view = StartMenu(ctx, self.get_db)
        await ctx.send("🏮 **Select Your Origin** 🏮\nYour choice will determine your struggle and your eventual power.", view=view)

async def setup(bot):
    await bot.add_cog(Core(bot))
