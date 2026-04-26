import discord
from discord.ext import commands
import sqlite3
import config

class Start(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def start(self, ctx):
        user_id = ctx.author.id
        conn = sqlite3.connect('murim.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        
        if c.fetchone():
            await ctx.send("You are already struggling within the Martial World.")
            conn.close()
            return

        view = BackgroundView(ctx.author)
        await ctx.send("Choose your past, Mortal. It will define your struggle.", view=view)
        conn.close()

class BackgroundView(discord.ui.View):
    def __init__(self, author):
        super().__init__()
        self.author = author

    async def register_user(self, interaction, bg, item):
        conn = sqlite3.connect('murim.db')
        c = conn.cursor()
        # I added the stats here so players start with 100 Vitality and 0 Ki/Taels
        c.execute("""INSERT INTO users (user_id, background, item_id, taels, ki, vitality) 
                     VALUES (?, ?, ?, 0, 0, 100)""", 
                  (interaction.user.id, bg, item))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"You have begun your journey as a **{bg}**. You carry a **{item}**.")

    @discord.ui.button(label="Laborer", style=discord.ButtonStyle.grey)
    async def laborer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id: return
        await self.register_user(interaction, "Laborer", "Torn Page")

    @discord.ui.button(label="Urchin", style=discord.ButtonStyle.grey)
    async def urchin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id: return
        await self.register_user(interaction, "Urchin", "Black Coin")

    @discord.ui.button(label="Hermit", style=discord.ButtonStyle.grey)
    async def hermit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id: return
        await self.register_user(interaction, "Hermit", "Glowing Fruit")

async def setup(bot):
    await bot.add_cog(Start(bot))
