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
        
        # FIXED: Using index 11 from the explicit SELECT statement
        self.current_taels = user_data[11]      
        
        self.add_item(ShopDropdown(self.background))

class ShopDropdown(discord.ui.Select):
    def __init__(self, background):
        options = [
            discord.SelectOption(label="Apothecary", description="Spiritual Pills", emoji="💊"),
            discord.SelectOption(label="Provisioner", description="Sustenance", emoji="🍱")
        ]
        
        if background == "Outcast":
            options.append(discord.SelectOption(label="Shady Dealer", description="Forbidden Goods", emoji="👺"))
            
        super().__init__(placeholder="Select a shop stall...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        view: BazaarView = self.view
        
        shops = {
            "Apothecary": [
                ("Spirit Gathering Dan", 100, "Refines the soul. Restores 20 Ki."),
                ("Jade Marrow Dew", 150, "Cool energy. Restores 50% Max Vitality.")
            ],
            "Provisioner": [
                ("Nine-Sun Restoration Soup", 30, "Warm soup. Restores 15 Vitality."),
                ("Dried Rations", 10, "Travelers food. Restores 5 Vitality.")
            ],
            "Shady Dealer": [
                ("Blood-Burning Catalyst", 1000, "Forbidden boost. +100 Ki but -50 HP.")
            ]
        }

        items = shops.get(selection, [])
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

        view.current_taels = new_taels
        main_embed = interaction.message.embeds[0]
        main_embed.description = f"💰 Your Taels: **{new_taels}**"
        
        self.placeholder = f"✅ Bought {item_name}!"
        
        await interaction.response.edit_message(embed=main_embed, view=view)
        await interaction.followup.send(f"🛍️ You purchased **{item_name}** for {item_price} Taels!", ephemeral=True)

class Bazaar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="bazaar", description="Visit the marketplace.")
    async def bazaar(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        # FIXED: Explicitly selecting columns to ensure Taels are at index 11
        user_data = c.execute("""
            SELECT 
                user_id, background, rank, stage, ki, 
                mastery, last_refresh, hp, vitality, active_tech, 
                profession, taels, item_id 
            FROM users WHERE user_id = ?
        """, (ctx.author.id,)).fetchone()
        conn.close()

        if not user_data:
            return await ctx.send("❌ You are not registered.", ephemeral=True)

        embed = discord.Embed(
            title="🏮 The Great Bazaar",
            description=f"💰 Your Taels: **{user_data[11]}**\n\nWelcome to the market. Select a stall below.",
            color=0x700000
        )
        
        view = BazaarView(ctx, user_data, self.get_db)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Bazaar(bot))
