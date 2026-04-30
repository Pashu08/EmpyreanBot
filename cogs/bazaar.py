import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class BazaarView(discord.ui.View):
    def __init__(self, ctx, user_data, db_func):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user_id = ctx.user.id if isinstance(ctx, discord.Interaction) else ctx.author.id
        self.get_db = db_func
        self.background = user_data[1] 
        
        # FIXED: Specifically targeting the Taels column to avoid the "Initial" text bug
        self.current_taels = user_data[11]      
        
        self.add_item(ShopDropdown(self.background))

class ShopDropdown(discord.ui.Select):
    def __init__(self, background):
        options = [
            discord.SelectOption(label="Apothecary", description="Pills and Medicines", emoji="💊"),
            discord.SelectOption(label="Provisioner", description="Food and Recovery", emoji="🍱")
        ]
        
        if background == "Outcast":
            options.append(discord.SelectOption(label="Shady Dealer", description="Forbidden Goods", emoji="👺"))
            
        super().__init__(placeholder="Select a shop stall...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        view: BazaarView = self.view
        
        shops = {
            "Apothecary": [
                ("Qi Condensing Pill", 100, "Restores 20 Ki instantly."),
                ("Vitality Elixir", 150, "Restores 50% Max Vitality.")
            ],
            "Provisioner": [
                ("Herbal Soup", 30, "Minor Vitality recovery."),
                ("Dried Rations", 10, "Cheap endurance food.")
            ],
            "Shady Dealer": [
                ("Demonic Essence", 1000, "Huge Ki gain, but costs 50 HP.")
            ]
        }

        items = shops.get(selection, [])
        # Displaying the actual numerical Taels
        embed = discord.Embed(
            title=f"🏪 Bazaar: {selection}", 
            description=f"💰 Your Taels: **{view.current_taels}**",
            color=0x700000
        )
        
        for item in view.children[:]:
            if isinstance(item, ItemSelect):
                view.remove_item(item)

        view.add_item(ItemSelect(items, view.get_db))

        for name, price, desc in items:
            embed.add_field(name=f"{name} — {price} Taels", value=desc, inline=False)
            
        await interaction.response.edit_message(embed=embed, view=view)

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
        view: BazaarView = self.view
        
        conn = self.get_db()
        c = conn.cursor()
        
        # We query specifically for Taels and Items to be 100% sure we have numbers
        user = c.execute("SELECT taels, item_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        
        if not user:
            return await interaction.response.send_message("❌ User not found.", ephemeral=True)
            
        current_taels, current_inv = user

        if current_taels < item_price:
            return await interaction.response.send_message(f"❌ You need {item_price} Taels (You have {current_taels}).", ephemeral=True)

        new_taels = current_taels - item_price
        new_inv = f"{current_inv}, {item_name}" if current_inv and current_inv != "None" else item_name
        
        c.execute("UPDATE users SET taels = ?, item_id = ? WHERE user_id = ?", (new_taels, new_inv, user_id))
        conn.commit()
        conn.close()

        # Update the live view so the next stall you click also shows the right amount
        view.current_taels = new_taels
        
        # Update the text on the current screen
        main_embed = interaction.message.embeds[0]
        main_embed.description = f"💰 Your Taels: **{new_taels}**"
        
        self.placeholder = f"✅ Bought {item_name}!"
        
        await interaction.response.edit_message(embed=main_embed, view=view)
        await interaction.followup.send(f"🛍️ You bought **{item_name}** for {item_price} Taels!", ephemeral=True)

class Bazaar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="bazaar", description="Visit the marketplace.")
    async def bazaar(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        # Fetching all columns for the specific user
        user_data = c.execute("SELECT * FROM users WHERE user_id = ?", (ctx.author.id,)).fetchone()
        conn.close()

        if not user_data:
            return await ctx.send("❌ You are not registered.", ephemeral=True)

        # user_data[11] is the Taels column in your DB
        embed = discord.Embed(
            title="🏮 The Great Bazaar",
            description=f"💰 Your Taels: **{user_data[11]}**\n\nWelcome to the market. Select a stall below.",
            color=0x700000
        )
        
        view = BazaarView(ctx, user_data, self.get_db)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Bazaar(bot))
