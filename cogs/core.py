import discord
from discord.ext import commands
import sqlite3

class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()

    def get_db(self):
        return sqlite3.connect('murim.db')

    def init_db(self):
        """Checks and adds missing columns automatically."""
        conn = self.get_db()
        c = conn.cursor()
        # Create table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, background TEXT, rank TEXT, 
                      item_id TEXT, taels INTEGER, ki INTEGER, vitality INTEGER, hp INTEGER)''')
        
        # Auto-add missing columns if they were forgotten in previous versions
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        required_columns = {
            "rank": "TEXT DEFAULT 'The Bound (Mortal)'",
            "hp": "INTEGER DEFAULT 100",
            "item_id": "TEXT",
            "taels": "INTEGER DEFAULT 0",
            "ki": "INTEGER DEFAULT 0",
            "vitality": "INTEGER DEFAULT 100"
        }

        for col, definition in required_columns.items():
            if col not in columns:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        
        conn.commit()
        conn.close()

    @commands.hybrid_command(name="start")
    async def start(self, ctx, background: str):
        """Starts the journey with correct items."""
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT user_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        if user: return await ctx.send("❌ You are already walking the path.")

        starters = {"Laborer": "Torn Page", "Urchin": "Black Coin", "Hermit": "Glowing Fruit"}
        item = starters.get(background, "Stick")
        
        c.execute("INSERT INTO users (user_id, background, rank, item_id, taels, ki, vitality, hp) VALUES (?, ?, ?, ?, 0, 0, 100, 100)",
                  (ctx.author.id, background, "The Bound (Mortal)", item))
        conn.commit()
        conn.close()
        await ctx.send(f"✅ Journey started as **{background}** with **{item}**.")

async def setup(bot):
    await bot.add_cog(Core(bot))
