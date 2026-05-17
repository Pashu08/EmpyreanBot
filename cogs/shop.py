import discord
from discord.ext import commands
import datetime
from utils.db import add_item, remove_item, has_item, get_inventory, get_user_stat, update_user_stat, get_bot_setting, is_user_banned
from utils.helpers import format_embed_color
from utils.constants import SHOP_ITEMS
import config

print("[DEBUG] shop.py: Loading Shop cog...")

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.give_cooldowns = {}  # user_id -> datetime
        print("[DEBUG] Shop cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_shop", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Shop"), ephemeral=True)
        return enabled

    # ==========================================
    # BROWSING: !bazaar (read‑only shop menu)
    # ==========================================
    @commands.hybrid_command(name="bazaar", aliases=["bz"], description="Browse the market stalls.")
    async def bazaar(self, ctx):
        print(f"[DEBUG] shop.bazaar: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        embed = discord.Embed(
            title="🏮 The Great Bazaar",
            description="Use `!buy <item> [quantity]` to purchase.\n"
                        "Example: `!buy \"Spirit Gathering Dan\" 2`\n\n"
                        "**Apothecary** (💊)\n"
                        "• Spirit Gathering Dan – 100 Taels (restores 20 Ki)\n"
                        "• Jade Marrow Dew – 150 Taels (restores 50% Max Vitality)\n"
                        "• Qi Pill (small) – 50 Taels (restores 10 Ki)\n"
                        "• Muscle Recovery Elixir – 80 Taels (restores 20 Vitality)\n\n"
                        "**Provisioner** (🍱)\n"
                        "• Nine-Sun Restoration Soup – 30 Taels (restores 15 Vitality)\n"
                        "• Dried Rations – 10 Taels (restores 5 Vitality)\n"
                        "• Iron Bandage – 25 Taels (restores 10 HP)\n"
                        "• Herbal Tea – 20 Taels (restores 10 Vitality)\n\n"
                        "**Shady Dealer** (👺) – for Outcasts only\n"
                        "• Blood-Burning Catalyst – 1000 Taels (+100 Ki, -50 HP) – Bound item\n"
                        "• Broken Technique Scroll – 500 Taels (+5% Mastery, one‑time use)",
            color=format_embed_color("main")
        )
        embed.set_footer(text="Use `!search <item>` to find where an item is sold.")
        await ctx.send(embed=embed)

    # ==========================================
    # BUY: !buy <item> [quantity]
    # ==========================================
    @commands.hybrid_command(name="buy", description="Purchase an item.")
    async def buy(self, ctx, item_name: str, quantity: int = 1):
        print(f"[DEBUG] shop.buy: {ctx.author.id} wants {quantity} of {item_name}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        # Find item in SHOP_ITEMS (case‑insensitive)
        item_key = None
        item_data = None
        for key, data in SHOP_ITEMS.items():
            if key.lower() == item_name.lower():
                item_key = key
                item_data = data
                break
        if not item_data:
            return await ctx.send(f"❌ Item `{item_name}` not found. Use `!search` to find items.", ephemeral=True)

        price = item_data["price"]
        shop_name = item_data.get("shop", "Unknown")
        total_cost = price * quantity

        # Check if player can buy from this shop (Outcast restriction)
        if shop_name == "Shady Dealer":
            user_bg = await get_user_stat(self.bot.db, ctx.author.id, "background")
            if user_bg != "Outcast":
                return await ctx.send("❌ Only **Outcasts** can buy from the Shady Dealer.", ephemeral=True)

        # Check Taels
        taels = await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0
        if taels < total_cost:
            return await ctx.send(f"❌ You need **{total_cost}** Taels (you have {taels}).", ephemeral=True)

        # Confirm for expensive items (>500 Taels)
        if total_cost > 500:
            view = discord.ui.View(timeout=30)
            confirm_btn = discord.ui.Button(label="✅ Confirm", style=discord.ButtonStyle.success)
            cancel_btn = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.danger)

            async def confirm_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ Not your transaction.", ephemeral=True)
                await interaction.response.edit_message(content="Processing...", view=None)
                await self._process_buy(ctx, item_key, quantity, total_cost, shop_name)
                view.stop()

            async def cancel_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ Not your transaction.", ephemeral=True)
                await interaction.response.edit_message(content="❌ Purchase cancelled.", view=None)
                view.stop()

            confirm_btn.callback = confirm_callback
            cancel_btn.callback = cancel_callback
            view.add_item(confirm_btn)
            view.add_item(cancel_btn)
            await ctx.send(f"⚠️ This purchase costs **{total_cost}** Taels. Confirm?", view=view, ephemeral=True)
            return

        await self._process_buy(ctx, item_key, quantity, total_cost, shop_name)

    async def _process_buy(self, ctx, item_key, quantity, total_cost, shop_name):
        """Deduct Taels and add item to inventory."""
        # Deduct Taels
        new_taels = (await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0) - total_cost
        await update_user_stat(self.bot.db, ctx.author.id, "taels", new_taels)

        # Check if item is bound (Blood-Burning Catalyst is bound)
        is_bound = 1 if item_key == "Blood-Burning Catalyst" else 0

        # Add to inventory (using the inventory table with bound flag)
        db = self.bot.db
        async with db.execute(
            "INSERT INTO inventory (user_id, item_name, quantity, bound) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?",
            (ctx.author.id, item_key, quantity, is_bound, quantity)
        ) as cursor:
            await db.commit()

        embed = discord.Embed(
            title="🛍️ Purchase Complete",
            description=f"You bought **{quantity}x {item_key}** from the **{shop_name}** for **{total_cost}** Taels.",
            color=format_embed_color("win")
        )
        if is_bound:
            embed.add_field(name="📜 Bound Item", value="This item cannot be traded or sold.", inline=False)
        await ctx.send(embed=embed)

    # ==========================================
    # SEARCH: !search <item>
    # ==========================================
    @commands.hybrid_command(name="search", description="Find which shop sells an item.")
    async def search(self, ctx, item_name: str):
        print(f"[DEBUG] shop.search: {ctx.author.id} searching for {item_name}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        found = []
        for key, data in SHOP_ITEMS.items():
            if item_name.lower() in key.lower():
                shop = data.get("shop", "Unknown")
                price = data.get("price", 0)
                found.append(f"**{key}** – {price} Taels ({shop})")

        if not found:
            return await ctx.send(f"❌ No item matching `{item_name}` found.", ephemeral=True)

        embed = discord.Embed(
            title=f"🔍 Search results for '{item_name}'",
            description="\n".join(found[:10]),
            color=format_embed_color("teal")
        )
        await ctx.send(embed=embed, ephemeral=True)

    # ==========================================
    # INVENTORY: !inventory (alias !inv)
    # ==========================================
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="View your items.")
    async def inventory(self, ctx):
        print(f"[DEBUG] shop.inventory: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        inv = await get_inventory(self.bot.db, ctx.author.id)
        if not inv:
            return await ctx.send("🎒 Your inventory is empty.", ephemeral=True)

        taels = await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0

        embed = discord.Embed(
            title=f"🎒 Inventory: {ctx.author.name}",
            description=f"💰 Taels: {taels}",
            color=format_embed_color("main")
        )
        for item in inv:
            bound_status = " (bound)" if item.get('bound') else ""
            embed.add_field(
                name=f"{item['name']}{bound_status}",
                value=f"Quantity: {item['quantity']}",
                inline=True
            )
        await ctx.send(embed=embed)

    # ==========================================
    # USE: !use <item>
    # ==========================================
    @commands.hybrid_command(name="use", description="Consume an item.")
    async def use(self, ctx, item_name: str):
        print(f"[DEBUG] shop.use: {ctx.author.id} using {item_name}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        # Find item in inventory (case‑insensitive)
        inv = await get_inventory(self.bot.db, ctx.author.id)
        target_item = None
        for item in inv:
            if item['name'].lower() == item_name.lower():
                target_item = item
                break
        if not target_item:
            return await ctx.send(f"❌ You don't have `{item_name}`.", ephemeral=True)

        # Get item effect from SHOP_ITEMS
        item_key = target_item['name']
        item_data = SHOP_ITEMS.get(item_key)
        if not item_data:
            return await ctx.send(f"❓ `{item_key}` has no known effect.", ephemeral=True)

        # Apply effect
        db = self.bot.db
        user_id = ctx.author.id
        rank = await get_user_stat(db, user_id, "rank") or "The Bound (Mortal)"
        effect = item_data.get("effect", {})

        # Get current stats
        ki = await get_user_stat(db, user_id, "ki") or 0
        hp = await get_user_stat(db, user_id, "hp") or 0
        vit = await get_user_stat(db, user_id, "vitality") or 0
        mastery = await get_user_stat(db, user_id, "mastery") or 0.0

        # Apply changes
        new_ki = ki
        new_hp = hp
        new_vit = vit
        new_mastery = mastery
        effect_msg = ""

        if "ki" in effect:
            new_ki = min(await get_user_stat(db, user_id, "ki_cap") or 1000, ki + effect["ki"])
            effect_msg += f"✨ +{effect['ki']} Ki. "
        if "hp" in effect:
            new_hp = max(1, hp + effect["hp"])
            effect_msg += f"🩸 {effect['hp']} HP. "
        if "vit" in effect:
            vit_cap = (await get_user_stat(db, user_id, "vit_cap") or 100)
            new_vit = min(vit_cap, vit + effect["vit"])
            effect_msg += f"❤️ +{effect['vit']} Vitality. "
        if "vit_pct" in effect:
            vit_cap = (await get_user_stat(db, user_id, "vit_cap") or 100)
            gain = int(vit_cap * effect["vit_pct"])
            new_vit = min(vit_cap, vit + gain)
            effect_msg += f"❤️ +{gain} Vitality ({int(effect['vit_pct']*100)}%). "
        if "mastery" in effect:
            new_mastery = min(100.0, mastery + effect["mastery"])
            effect_msg += f"📖 +{effect['mastery']}% Mastery. "

        # Update database
        await update_user_stat(db, user_id, "ki", new_ki)
        await update_user_stat(db, user_id, "hp", new_hp)
        await update_user_stat(db, user_id, "vitality", new_vit)
        await update_user_stat(db, user_id, "mastery", new_mastery)

        # Remove one instance of the item
        await remove_item(db, user_id, item_key, 1)

        embed = discord.Embed(
            title="🎒 Item Used",
            description=f"You used **{item_key}**.\n\n{effect_msg}",
            color=format_embed_color("win")
        )
        await ctx.send(embed=embed)

    # ==========================================
    # SELL: !sell <item> [quantity]
    # ==========================================
    @commands.hybrid_command(name="sell", description="Sell an item for half its price.")
    async def sell(self, ctx, item_name: str, quantity: int = 1):
        print(f"[DEBUG] shop.sell: {ctx.author.id} selling {quantity}x {item_name}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        # Check if item exists in inventory
        inv = await get_inventory(self.bot.db, ctx.author.id)
        target_item = None
        for item in inv:
            if item['name'].lower() == item_name.lower():
                target_item = item
                break
        if not target_item:
            return await ctx.send(f"❌ You don't have `{item_name}`.", ephemeral=True)

        # Bound items cannot be sold
        if target_item.get('bound'):
            return await ctx.send("❌ Bound items cannot be sold.", ephemeral=True)

        if target_item['quantity'] < quantity:
            return await ctx.send(f"❌ You only have {target_item['quantity']} of that item.", ephemeral=True)

        # Get price from SHOP_ITEMS
        item_key = target_item['name']
        item_data = SHOP_ITEMS.get(item_key)
        if not item_data:
            return await ctx.send(f"❓ Cannot determine price for {item_key}.", ephemeral=True)

        price = item_data.get("price", 0)
        sell_price = int(price * quantity * 0.5)  # half price
        if sell_price < 1:
            sell_price = 1

        # Add Taels and remove item
        new_taels = (await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0) + sell_price
        await update_user_stat(self.bot.db, ctx.author.id, "taels", new_taels)
        await remove_item(self.bot.db, ctx.author.id, item_key, quantity)

        embed = discord.Embed(
            title="💰 Item Sold",
            description=f"You sold **{quantity}x {item_key}** for **{sell_price}** Taels.",
            color=format_embed_color("gold")
        )
        await ctx.send(embed=embed)

    # ==========================================
    # GIVE: !give @user <item> [quantity]
    # ==========================================
    @commands.hybrid_command(name="give", description="Give an item to another player.")
    async def give(self, ctx, recipient: discord.Member, item_name: str, quantity: int = 1):
        print(f"[DEBUG] shop.give: {ctx.author.id} giving {quantity}x {item_name} to {recipient.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        # Restriction 1: Cannot give to self
        if recipient.id == ctx.author.id:
            return await ctx.send("❌ You cannot give items to yourself.", ephemeral=True)

        # Restriction 2: Minimum rank (Third-Rate Warrior)
        rank = await get_user_stat(self.bot.db, ctx.author.id, "rank") or "The Bound (Mortal)"
        if "Third-Rate" not in rank and "Second-Rate" not in rank and "First-Rate" not in rank and "Peak Master" not in rank:
            return await ctx.send("❌ You must be at least **Third-Rate Warrior** to give items.", ephemeral=True)

        # Restriction 3: Daily give limit (3 per day)
        today = datetime.datetime.now().date().isoformat()
        give_date = await get_user_stat(self.bot.db, ctx.author.id, "daily_give_date")
        give_count = await get_user_stat(self.bot.db, ctx.author.id, "daily_give_count") or 0
        if give_date != today:
            give_count = 0
            await update_user_stat(self.bot.db, ctx.author.id, "daily_give_date", today)
        if give_count >= 3:
            return await ctx.send("❌ You have reached your daily give limit (3). Try again tomorrow.", ephemeral=True)

        # Restriction 4: Cooldown (5 minutes)
        if ctx.author.id in self.give_cooldowns:
            last_used = self.give_cooldowns[ctx.author.id]
            if datetime.datetime.now() < last_used:
                remaining = int((last_used - datetime.datetime.now()).total_seconds())
                return await ctx.send(f"⏳ Please wait {remaining} seconds before using `!give` again.", ephemeral=True)

        # Check if item exists in inventory and is not bound
        inv = await get_inventory(self.bot.db, ctx.author.id)
        target_item = None
        for item in inv:
            if item['name'].lower() == item_name.lower():
                target_item = item
                break
        if not target_item:
            return await ctx.send(f"❌ You don't have `{item_name}`.", ephemeral=True)

        if target_item.get('bound'):
            return await ctx.send("❌ Bound items cannot be given away.", ephemeral=True)

        if target_item['quantity'] < quantity:
            return await ctx.send(f"❌ You only have {target_item['quantity']} of that item.", ephemeral=True)

        # Remove from giver, add to recipient
        await remove_item(self.bot.db, ctx.author.id, target_item['name'], quantity)
        for _ in range(quantity):
            await add_item(self.bot.db, recipient.id, target_item['name'], 1)

        # Update daily give count and cooldown
        await update_user_stat(self.bot.db, ctx.author.id, "daily_give_count", give_count + 1)
        self.give_cooldowns[ctx.author.id] = datetime.datetime.now() + datetime.timedelta(minutes=5)

        embed = discord.Embed(
            title="🎁 Item Given",
            description=f"You gave **{quantity}x {target_item['name']}** to {recipient.mention}.",
            color=format_embed_color("win")
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Shop(bot))
    print("[DEBUG] shop.py: Setup complete")