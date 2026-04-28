import discord
from discord.ext import commands
import sqlite3
import config
import os

# ==========================================
# DATABASE INITIALIZATION & PHASE 2 MIGRATION
# ==========================================
def init_db():
    conn = sqlite3.connect('murim.db')
    c = conn.cursor()
    
    # 1. Create the base table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    background TEXT,
                    rank_id INTEGER DEFAULT 0,
                    rank TEXT DEFAULT 'The Bound (Mortal)',
                    item_id TEXT,
                    taels INTEGER DEFAULT 0,
                    ki INTEGER DEFAULT 0,
                    vitality INTEGER DEFAULT 100,
                    hp INTEGER DEFAULT 100
                )''')
    
    # 2. PHASE 2 MIGRATION: ADDING NEW COLUMNS
    # This ensures old databases get the new columns without crashing
    new_columns = [
        ("stage", "TEXT DEFAULT 'Initial'"),
        ("last_refresh", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("mastery", "REAL DEFAULT 0.0"),
        ("active_tech", "TEXT DEFAULT 'None'"),
        ("boss_flags", "TEXT DEFAULT ''")
    ]
    
    for col_name, col_type in new_columns:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Migration: Added column [{col_name}] to users table.")
        except sqlite3.OperationalError:
            # Column already exists, skipping
            pass

    conn.commit()
    conn.close()

# Initialize the database before the bot starts
init_db()

# ==========================================
# BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MurimBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.PREFIX, intents=intents)

    async def setup_hook(self):
        # Automatically loads every file inside the cogs folder
        print("--- Loading Techniques (Cogs) ---")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Loaded Cog: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load Cog {filename}: {e}")

    async def on_ready(self):
        print(f"\n--- Murim: Empyrean Ascent is Online ---")
        print(f"Logged in as: {self.user.name} (ID: {self.user.id})")
        print(f"Phase 2 Engine: Active")
        print("------------------------------------------")

bot = MurimBot()
bot.run(config.TOKEN)
