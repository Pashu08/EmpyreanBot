import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

class Cultivation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # ==========================================
    # HYBRID COMMAND: breakthrough
    # ==========================================
    @commands.hybrid_command(name="breakthrough", description="Attempt to break the chains of The Bound.")
    async def breakthrough(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT background, ki, item_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user:
            conn.close()
            return await ctx.send("Use /start first.")
        
        bg, ki, item = user[0], user[1], user[2]

        if ki < 100:
            conn.close()
            return await ctx.send(f"❌ Your Ki is only **{ki}/100**. Your foundation is too weak to attempt ascension.")

        # --- THE NARRATIVE MINI-GAME ---
        score = 0
        await ctx.send("🌀 **The Breakthrough Begins.** The energy within you roars like a trapped beast. Respond!")

        # PROMPT 1: THE SURGE
        # -------------------
        p1_msg = (
            "**PROMPT 1: THE SURGE**\n"
            "Raw energy floods your meridians! How do you handle the pressure?\n"
            "1️⃣ Endure the pressure through grit.\n"
            "2️⃣ Trick the flow into a side meridian.\n"
            "3️⃣ Let the energy roar through naturally."
        )
        msg = await ctx.send(p1_msg)
        for emoji in ["1️⃣", "2️⃣", "3️⃣"]: await msg.add_reaction(emoji)

        def check(reaction, u): return u == ctx.author and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣"]
        
        try:
            res1, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            choice1 = str(res1.emoji)
            
            # Logic: Laborer=1, Urchin=2, Hermit=3
            if (choice1 == "1️⃣" and "Laborer" in bg) or \
               (choice1 == "2️⃣" and "Urchin" in bg) or \
               (choice1 == "3️⃣" and "Hermit" in bg):
                score += 1
                await ctx.send("✅ You managed the surge perfectly.")
            else:
                await ctx.send("⚠️ Your meridians groan under the strain...")
        except: return await ctx.send("⌛ You lost focus. The breakthrough failed.")

        # PROMPT 2: THE GATE
        # -------------------
        p2_msg = (
            "**PROMPT 2: THE GATE**\n"
            "You reach the spiritual barrier. How do you pass?\n"
            "1️⃣ Slowly wear down the barrier with steady breath.\n"
            "2️⃣ Look for a crack in the spiritual gate.\n"
            "3️⃣ Smash the gate with raw, wild intent."
        )
        msg2 = await ctx.send(p2_msg)
        for emoji in ["1️⃣", "2️⃣", "3️⃣"]: await msg2.add_reaction(emoji)

        try:
            res2, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            choice2 = str(res2.emoji)
            
            if (choice2 == "1️⃣" and "Laborer" in bg) or \
               (choice2 == "2️⃣" and "Urchin" in bg) or \
               (choice2 == "3️⃣" and "Hermit" in bg):
                score += 1
                await ctx.send("✅ The gate begins to crumble.")
            else:
                await ctx.send("⚠️ The barrier holds firm, vibrating painfully.")
        except: return await ctx.send("⌛ Exhaustion took you. The breakthrough failed.")

        # --- FINAL CALCULATION ---
        if score >= 2:
            # SUCCESS Logic
            new_rank = "Third-Rate Warrior"
            # Item Mutation Logic: Torn Page -> Jade Scripture; Black Coin -> Shadow Seal; Fruit -> Verdant Bone
            mutations = {
                "Torn Page": "Jade Scripture",
                "Black Coin": "Shadow Seal",
                "Glowing Fruit": "Verdant Bone"
            }
            new_item = mutations.get(item, item)
            
            c.execute("UPDATE users SET background = ?, item_id = ?, ki = 0 WHERE user_id = ?", (new_rank, new_item, ctx.author.id))
            await ctx.send(f"✨ **ASCENSION SUCCESS!** ✨\nYou have become a **{new_rank}**.\nYour {item} has mutated into a **{new_item}**!")
        else:
            # FAILURE Logic: Ki to 70, HP to 10
            c.execute("UPDATE users SET ki = 70, hp = 10 WHERE user_id = ?", (ctx.author.id,))
            await ctx.send("💥 **ASCENSION FAILURE!** 💥\nYour foundation cracked. Your Ki has leaked away and your body is broken (HP: 10).")

        conn.commit()
        conn.close()

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
