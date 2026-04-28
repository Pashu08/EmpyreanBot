import discord
from discord.ext import commands
import sqlite3
import config
import os

# ==========================================
# DATABASE INITIALIZATION & AUTO-MIGRATION
# ==========================================
def init_db():
    conn = sqlite3.connect('murim.db')
    c = conn.cursor()
    
    # 1. Create the base table with ALL current columns
    # This handles fresh installations perfectly
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    background TEXT,
                    rank_id INTEGER DEFAULT 0,
                    rank TEXT DEFAULT 'The Bound (Mortal)',
                    item_id TEXT,
                    taels INTEGER DEFAULT 0,
                    ki INTEGER DEFAULT 0,
                    vitality INTEGER DEFAULT 100,
                    hp INTEGER DEFAULT 100,
                    stage TEXT DEFAULT 'Initial',
                    last_refresh TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mastery REAL DEFAULT 0.0,
                    active_tech TEXT DEFAULT 'None',
                    boss_flags TEXT DEFAULT '',
                    profession TEXT DEFAULT 'None',
                    prof_rank TEXT DEFAULT 'Apprentice',
                    prof_xp INTEGER DEFAULT 0,
                    prof_req_xp INTEGER DEFAULT 1000
                )''')
    
    # 2. AUTO-MIGRATION LOOP
    # If the table already exists, this adds any missing columns automatically
    MIGRATIONS = [
        ("stage", "TEXT DEFAULT 'Initial'"),
        ("last_refresh", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("mastery", "REAL DEFAULT 0.0"),
        ("active_tech", "TEXT DEFAULT 'None'"),
        ("boss_flags", "TEXT DEFAULT ''"),
        ("profession", "TEXT DEFAULT 'None'"),
        ("prof_rank", "TEXT DEFAULT 'Apprentice'"),
        ("prof_xp", "INTEGER DEFAULT 0"),
        ("prof_req_xp", "INTEGER DEFAULT 1000")
    ]
    
    for col_name, col_type in MIGRATIONS:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"🛠️ Database Migration: Added missing column [{col_name}]")
        except sqlite3.OperationalError:
            # Column already exists, move to next
            pass

    conn.commit()
    conn.close()

# Run database setup
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
        print("--- Loading Empyrean Systems (Cogs) ---")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Loaded: {filename}")
                except Exception as e:
                    print(f"❌ Error Loading {filename}: {e}")

    async def on_ready(self):
        print(f"\n--- Murim: Empyrean Ascent is Online ---")
        print(f"Logged in as: {self.user.name}")
        print(f"Status: Database Sync Complete")
        print("------------------------------------------")

bot = MurimBot()
bot.run(config.TOKEN)
