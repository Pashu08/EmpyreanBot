import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class BazaarView(discord.ui.View):
    def __init__(self, ctx, user_data, db_func):
        super().__init__(timeout=60)
        self.ctx = ctx
        # Correctly getting user ID whether it's Context or Interaction
        self.user_id = ctx.user.id if isinstance(ctx, discord.Interaction) else ctx.author.id
        self.get_db = db_func
        self.background = user_data[1] # Background from DB
        self.taels = user_data[9]      # Taels from DB
        
        # Define the Shop Categories
        self.add_item(ShopDropdown(self.background))

class ShopDropdown(discord.ui.Select):
    def __init__(self, background):
        options = [
            discord.SelectOption(label="Apothecary", description="Pills and Medicines", emoji="💊"),
            discord.SelectOption(label="Scroll Merchant", description="Technique Manuals", emoji="📜"),
            discord.SelectOption(label="Provisioner", description="Food and Recovery", emoji="🍱")
        ]
        
        # THE OUTCAST STEALTH LOGIC
        if background == "Outcast":
            options.append(discord.SelectOption(label="Shady Dealer", description="Forbidden Goods", emoji="👺"))
            
        super().__init__(placeholder="Select a shop stall...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        view: BazaarView = self.view
        
        # Content for each shop
        shops = {
            "Apothecary": [
                ("Qi Condensing Pill", 100, "Restores 20 Ki instantly."),
                ("Vitality Elixir", 150, "Restores 50% Max Vitality.")
            ],
            "Scroll Merchant": [
                ("Mid-Tier: Iron Palm", 500, "Manual for advanced physical strikes."),
                ("Mid-Tier: Swift Step", 500, "Manual for advanced movement.")
            ],
            "Provisioner": [
                ("Herbal Soup", 30, "Minor Vitality recovery."),
                ("Dried Rations", 10, "Cheap endurance food.")
            ],
            "Shady Dealer": [
                ("Demonic Essence", 1000, "Huge Ki gain, but costs 50 HP."),
                ("Forbidden: Blood Blade", 2000, "A dangerous high-tier manual.")
            ]
        }

        items = shops.get(selection, [])
        embed = discord.Embed(title=f"🏪 Bazaar: {selection}", color=0x700000)
        
        # Clear existing item dropdowns if user switches categories
        for item in view.children[:]:
            if isinstance(item, ItemSelect):
                view.remove_item(item)

        # Add the Item Selection dropdown
        view.add_item(ItemSelect(items, view.get_db))

        for name, price, desc in items:
            embed.add_field(name=f"{name} — {price} Taels", value=desc, inline=False)
            
        await interaction.response.edit_message(embed=embed, view=view)

# --- NEW: ITEM SELECTION & PURCHASE LOGIC ---
class ItemSelect(discord.ui.Select):
    def __init__(self, items, db_func):
        self.get_db = db_func
        options = [
            discord.SelectOption(label=name, description=f"{price} Taels", value=f"{name}|{price}")
            for name, price, desc in items
        ]
        super().__init__(placeholder="Pick an item to buy...", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_name, item_price = self.values[0].split("|")
        item_price = int(item_price)
        user_id = interaction.user.id
        
        conn = self.get_db()
        c = conn.cursor()
        
        # Fetch money and inventory
        user = c.execute("SELECT taels, item_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        
        if not user:
            return await interaction.response.send_message("❌ User not found.", ephemeral=True)
            
        current_taels, current_inv = user

        # 1. Check Funds
        if current_taels < item_price:
            return await interaction.response.send_message(f"❌ You need {item_price} Taels (Current: {current_taels})", ephemeral=True)

        # 2. Check Ownership (Don't buy the same manual twice)
        if current_inv and item_name in current_inv:
            return await interaction.response.send_message("❌ You already own this item.", ephemeral=True)

        # 3. Complete Transaction
        new_taels = current_taels - item_price
        new_inv = f"{current_inv}, {item_name}" if current_inv != "None" else item_name
        
        c.execute("UPDATE users SET taels = ?, item_id = ? WHERE user_id = ?", (new_taels, new_inv, user_id))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ Purchased **{item_name}**! (-{item_price} Taels)", ephemeral=True)

class Bazaar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # UPDATED: Changed to hybrid_command to support !bazaar
    @commands.hybrid_command(name="bazaar", description="Visit the marketplace to spend your Taels.")
    async def bazaar(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        user_data = c.execute("SELECT * FROM users WHERE user_id = ?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user_data:
            return await ctx.send("❌ You are not registered.", ephemeral=True)

        embed = discord.Embed(
            title="🏮 The Great Bazaar",
            description=f"Your Taels: **{user_data[9]}**\n\nWelcome to the market. Select a stall below to browse goods.",
            color=0x700000
        )
        
        # ctx handles both prefix and slash inputs
        view = BazaarView(ctx, user_data, self.get_db)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Bazaar(bot))
