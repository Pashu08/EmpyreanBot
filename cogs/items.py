import discord
from discord.ext import commands
import sqlite3

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="inventory", description="View your currency and gathered treasures.")
    async def inventory(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        row = c.execute("SELECT taels, item_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        conn.close()

        if not row:
            return await ctx.send("❌ You have not started your journey.", ephemeral=True)

        taels, item_string = row
        items_display = "*Your pockets are empty.*"
        if item_string and item_string != "None":
            items_display = "\n".join([f"• {i.strip()}" for i in item_string.split(",") if i.strip()])

        embed = discord.Embed(title=f"🎒 Inventory: {ctx.author.name}", color=0x2c3e50)
        embed.add_field(name="Wealth", value=f"💰 **Taels:** {taels}", inline=False)
        embed.add_field(name="Possessions", value=items_display, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="use", description="Consume an item from your inventory.")
    async def use(self, ctx, *, item_name: str):
        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("SELECT item_id, ki, hp, vitality, rank FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()

        if not user or not user[0] or user[0] == "None":
            return await ctx.send("❌ Your inventory is empty.")

        inv_string, ki, hp, vit, rank = user
        inventory = [i.strip() for i in inv_string.split(",") if i.strip()]

        # Search for the item (Case-insensitive)
        target_item = next((i for i in inventory if i.lower() == item_name.lower()), None)

        if not target_item:
            return await ctx.send(f"❌ You do not possess '**{item_name}**'.")

        # --- ITEM EFFECTS LOGIC ---
        effect_msg = ""
        new_ki, new_hp, new_vit = ki, hp, vit
        
        # Caps based on rank
        caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 1000} # Simplified for now
        ki_cap = caps.get(rank, 3000)
        vit_cap = 100 if "Mortal" in rank else 300

        if target_item == "Spirit Gathering Dan":
            new_ki = min(ki_cap, ki + 20)
            effect_msg = "✨ The pill dissolves into pure energy! **+20 Ki**."
        elif target_item == "Jade Marrow Dew":
            new_vit = min(vit_cap, vit + (vit_cap * 0.5))
            effect_msg = "🧪 A cool sensation washes over you. **+50% Vitality restored**."
        elif target_item == "Nine-Sun Restoration Soup":
            new_vit = min(vit_cap, vit + 15)
            effect_msg = "🍵 A warm energy fills your meridians. **+15 Vitality**."
        elif target_item == "Blood-Burning Catalyst":
            new_ki = min(ki_cap, ki + 100)
            new_hp = max(1, hp - 50)
            effect_msg = "👺 You consume the forbidden essence. **+100 Ki**, but your body trembles in pain! **-50 HP**."
        else:
            return await ctx.send("❓ This item has no known use yet.")

        # --- UPDATE INVENTORY (Remove 1 instance) ---
        inventory.remove(target_item)
        new_inv_string = ", ".join(inventory) if inventory else "None"

        c.execute("""UPDATE users SET item_id=?, ki=?, hp=?, vitality=? WHERE user_id=?""",
                  (new_inv_string, new_ki, new_hp, new_vit, ctx.author.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title="🎒 Item Consumed", description=f"You used **{target_item}**.\n\n{effect_msg}", color=0x00FF00)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Items(bot))
