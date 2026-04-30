import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class BazaarView(discord.ui.View):
    def __init__(self, interaction, user_data, db_func):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.user_id = interaction.user.id
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
        
        for name, price, desc in items:
            embed.add_field(name=f"{name} — {price} Taels", value=desc, inline=False)
            
        await interaction.response.edit_message(embed=embed, view=view)

class Bazaar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @app_commands.command(name="bazaar", description="Visit the marketplace to spend your Taels.")
    async def bazaar(self, interaction: discord.Interaction):
        conn = self.get_db()
        c = conn.cursor()
        user_data = c.execute("SELECT * FROM users WHERE user_id = ?", (interaction.user.id,)).fetchone()
        conn.close()

        if not user_data:
            return await interaction.response.send_message("❌ You are not registered.", ephemeral=True)

        embed = discord.Embed(
            title="🏮 The Great Bazaar",
            description=f"Your Taels: **{user_data[9]}**\n\nWelcome to the market. Select a stall below to browse goods.",
            color=0x700000
        )
        
        view = BazaarView(interaction, user_data, self.get_db)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Bazaar(bot))
