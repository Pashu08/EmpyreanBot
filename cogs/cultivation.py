import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio

class Cultivation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="breakthrough", description="Attempt to break the chains of The Bound.")
    async def breakthrough(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, rank, ki, item_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user:
            conn.close()
            return await ctx.send("Use /start first.")
        
        bg, current_rank, ki, item = user[0], user[1], user[2], user[3]

        if ki < 100:
            conn.close()
            return await ctx.send(f"❌ Your Ki is only **{ki}/100**. Your foundation is too weak.")

        if "Third-Rate" in current_rank:
            conn.close()
            return await ctx.send("✨ You have already opened your meridians.")

        # --- THE NARRATIVE MINI-GAME ---
        score = 0
        def check(reaction, u): return u == ctx.author and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣"]

        await ctx.send("🌀 **The Breakthrough Begins.** The energy within you roars like a trapped beast!")

        # PROMPT 1: THE SURGE
        p1_msg = await ctx.send("**PROMPT 1: THE SURGE**\n1️⃣ Endure with grit.\n2️⃣ Trick the flow.\n3️⃣ Let it roar naturally.")
        for e in ["1️⃣", "2️⃣", "3️⃣"]: await p1_msg.add_reaction(e)
        try:
            res, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            if (str(res.emoji) == "1️⃣" and bg == "Laborer") or \
               (str(res.emoji) == "2️⃣" and bg == "Outcast") or \
               (str(res.emoji) == "3️⃣" and bg == "Hermit"):
                score += 1
        except asyncio.TimeoutError: return await ctx.send("⌛ Focus lost.")

        # PROMPT 2: THE GATE
        p2_msg = await ctx.send("**PROMPT 2: THE GATE**\n1️⃣ Wear it down steadily.\n2️⃣ Find a crack.\n3️⃣ Smash it with wild intent.")
        for e in ["1️⃣", "2️⃣", "3️⃣"]: await p2_msg.add_reaction(e)
        try:
            res, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            if (str(res.emoji) == "1️⃣" and bg == "Laborer") or \
               (str(res.emoji) == "2️⃣" and bg == "Outcast") or \
               (str(res.emoji) == "3️⃣" and bg == "Hermit"):
                score += 1
        except asyncio.TimeoutError: return await ctx.send("⌛ Focus lost.")

        # PROMPT 3: THE VESSEL
        p3_msg = await ctx.send("**PROMPT 3: THE VESSEL**\n1️⃣ Compress it.\n2️⃣ Circulate through skin.\n3️⃣ Dissolve into soul.")
        for e in ["1️⃣", "2️⃣", "3️⃣"]: await p3_msg.add_reaction(e)
        try:
            res, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            if (str(res.emoji) == "1️⃣" and bg == "Laborer") or \
               (str(res.emoji) == "2️⃣" and bg == "Outcast") or \
               (str(res.emoji) == "3️⃣" and bg == "Hermit"):
                score += 1
        except asyncio.TimeoutError: return await ctx.send("⌛ Focus lost.")

        # --- FINAL CALCULATION ---
        if score >= 2:
            new_rank = "Third-Rate Warrior"
            mutations = {"Torn Page": "Jade Scripture", "Black Coin": "Shadow Seal", "Glowing Fruit": "Verdant Bone"}
            new_item = mutations.get(item, item)
            
            c.execute("""UPDATE users SET rank = ?, item_id = ?, ki = 0, hp = 300, vitality = 300 
                         WHERE user_id = ?""", (new_rank, new_item, ctx.author.id))
            await ctx.send(f"✨ **ASCENSION SUCCESS!** ✨\nYou are now a **{new_rank}**! HP/Vit increased to **300**.")
        else:
            c.execute("UPDATE users SET ki = 70, hp = 10 WHERE user_id = ?", (ctx.author.id,))
            await ctx.send("💥 **ASCENSION FAILURE!** 💥\nKi leaked to 70 and your HP is 10.")

        conn.commit()
        conn.close()

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
