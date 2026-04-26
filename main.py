import discord
from discord.ext import commands
import sqlite3
import config
import os

# Database Initialization
def init_db():
    conn = sqlite3.connect('murim.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    background TEXT,
                    rank_id INTEGER DEFAULT 0,
                    item_id TEXT,
                    taels INTEGER DEFAULT 0,
                    ki INTEGER DEFAULT 0,
                    vitality INTEGER DEFAULT 100,
                    hp INTEGER DEFAULT 100
                )''')
    conn.commit()
    conn.close()

init_db()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MurimBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.PREFIX, intents=intents)

    async def setup_hook(self):
        # Automatically loads every file inside the cogs folder
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loaded Cog: {filename}")

    async def on_ready(self):
        print(f"--- Murim: Empyrean Ascent is Online ---")

bot = MurimBot()
bot.run(config.TOKEN)
