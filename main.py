import discord
from discord.ext import commands
import aiosqlite
import config
import os
import asyncio

# ==========================================
# DATABASE: SELF-HEALING AUTO-MIGRATION
# ==========================================
async def init_db():
    async with aiosqlite.connect("murim.db") as conn:
        c = await conn.cursor()

        MASTER_SCHEMA = {
            "user_id": "INTEGER PRIMARY KEY",
            "background": "TEXT",
            "rank_id": "INTEGER DEFAULT 0",
            "rank": "TEXT DEFAULT 'The Bound (Mortal)'",
            "item_id": "TEXT",
            "taels": "INTEGER DEFAULT 0",
            "ki": "INTEGER DEFAULT 0",
            "vitality": "INTEGER DEFAULT 100",
            "hp": "INTEGER DEFAULT 100",
            "stage": "TEXT DEFAULT 'Initial'",
            "last_refresh": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "mastery": "REAL DEFAULT 0.0",
            "active_tech": "TEXT DEFAULT 'None'",
            "boss_flags": "TEXT DEFAULT ''",
            "profession": "TEXT DEFAULT 'None'",
            "prof_rank": "TEXT DEFAULT 'Apprentice'",
            "prof_xp": "INTEGER DEFAULT 0",
            "prof_req_xp": "INTEGER DEFAULT 1000",
            "combat_mastery": "REAL DEFAULT 0.0",
            "meridian_damage": "TEXT"
        }

        await c.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)"
        )

        await c.execute("PRAGMA table_info(users)")
        existing_columns_data = await c.fetchall()
        existing_columns = [info[1] for info in existing_columns_data]

        for col_name, col_type in MASTER_SCHEMA.items():
            if col_name not in existing_columns:
                try:
                    await c.execute(
                        f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                    )
                    print(f"🛠️ Added missing column: {col_name}")
                except Exception as e:
                    if col_name != "user_id":
                        print(f"⚠️ Failed to add {col_name}: {e}")

        await conn.commit()

# ==========================================
# BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MurimBot(commands.Bot):
    def __init__(self):
        self.config = config
        self.db = None

        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents
        )

    async def setup_hook(self):
        print("📦 Initializing Database...")
        await init_db()

        print("🔗 Opening Database Connection...")
        self.db = await aiosqlite.connect("murim.db")

        print("--- Loading Empyrean Systems (Cogs) ---")

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded: {filename}")
                except Exception as e:
                    print(f"❌ Error Loading {filename}: {e}")

    async def close(self):
        if self.db:
            await self.db.close()

        await super().close()

    async def on_ready(self):
        print("\n--- Murim: Empyrean Ascent is Online ---")
        print(f"Logged in as: {self.user.name}")
        print("Status: Database Sync Complete")
        print("------------------------------------------")

bot = MurimBot()
bot.run(config.TOKEN)