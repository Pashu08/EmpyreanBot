"""
commands/shop.py - Command logic for Shop cog
Contains all shop-related commands: bazaar, buy, sell, inventory, use, give, search, pouch.

This file handles:
- !pouch / !money / !wealth - Check your Taels
- !bazaar / !bz - Open the interactive shop menu
- !buy <item> [quantity] - Purchase items from shops
- !search <item> - Find which shop sells an item
- !inventory / !inv - View your items
- !use <item> - Consume an item from your inventory
- !sell <item> [quantity] - Sell items for half price
- !give @user <item> [quantity] - Give items to another player

All embeds are imported from embeds.shop_embeds.
All helpers are imported from backend.shop_helpers.
"""

import discord
from discord.ext import commands
import datetime
from typing import Optional

# Backend imports
from backend.db import (
    get_bot_setting, is_user_banned, get_user_stat, update_user_stat,
    add_item, remove_item, get_inventory
)
from backend.helpers import get_max_stats, format_embed_color
from backend.constants import SHOP_ITEMS
from backend.shop_helpers import (
    SHOP_INFO,
    GiveCooldownManager,
    ShopView,
    get_item_data,
    get_item_price,
    get_item_shop,
    calculate_sell_price,
    is_item_bound,
    can_access_shady_dealer,
    validate_shop_access,
    get_item_effect_preview,
    calculate_total_cost,
    find_item_in_inventory,
    search_items,
    can_give_items,
    get_rank_requirement_for_give,
    get_daily_give_limit,
    can_give_today
)

# Embed imports
from embeds.shop_embeds import (
    bazaar_main_embed,
    pouch_embed,
    purchase_confirmation_embed,
    purchase_complete_embed,
    item_used_embed,
    item_not_found_embed,
    item_sold_embed,
    cannot_sell_bound_item_embed,
    insufficient_quantity_embed,
    item_given_embed,
    give_limit_reached_embed,
    give_cooldown_embed,
    cannot_give_to_self_embed,
    cannot_give_to_banned_embed,
    rank_required_for_give_embed,
    search_results_embed,
    shop_feature_disabled_embed,
    item_not_for_sale_embed,
    shady_dealer_only_embed,
    insufficient_taels_embed,
    inventory_embed
)

import config

print("[DEBUG] commands/shop.py: Loading Shop commands...")


# ==========================================
# MAIN COG
# ==========================================

class Shop(commands.Cog):
    """
    Shop cog - Handles all shop, inventory, and item management.
    
    Features:
    - 3 shops (Apothecary, Provisioner, Shady Dealer for Outcasts)
    - Buy, sell, and use items
    - Give items to other players (3 per day, 5 min cooldown)
    - Search for items across all shops
    - Bound items (cannot be sold or given)
    
    Commands:
    - !pouch - Check your Taels
    - !bazaar - Open shop menu
    - !buy - Purchase items
    - !search - Find items
    - !inventory - View your items
    - !use - Consume items
    - !sell - Sell items
    - !give - Give items to others
    """
    
    def __init__(self, bot):
        """
        Initialize the Shop cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.give_cooldowns = GiveCooldownManager()
        print("[DEBUG] Shop cog initialized")
    
    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if shop feature is enabled.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        enabled = await get_bot_setting(self.bot.db, "toggle_shop", True)
        if not enabled:
            embed = shop_feature_disabled_embed()
            await ctx.send(embed=embed, ephemeral=True)
        return enabled
    
    async def _get_user_or_error(self, ctx: commands.Context, user_id: int):
        """
        Fetch user from database or send error.
        
        Args:
            ctx: Command context
            user_id: Discord user ID
            
        Returns:
            dict or None: User document if found, None otherwise
        """
        user = await self.bot.db.users.find_one({"user_id": user_id})
        if not user:
            await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)
            return None
        return user
    
    # ==========================================
    # COMMAND: POUCH
    # ==========================================
    
    @commands.hybrid_command(
        name="pouch",
        aliases=["money", "wealth"],
        description="Check your Taels."
    )
    async def pouch(self, ctx: commands.Context):
        """
        Check how many Taels you have.
        
        Usage: !pouch, !money, or !wealth
        """
        print(f"[DEBUG] shop.pouch: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        taels = await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0
        
        embed = pouch_embed(taels)
        await ctx.send(embed=embed, ephemeral=True)
    
    # ==========================================
    # COMMAND: BAZAAR
    # ==========================================
    
    @commands.hybrid_command(
        name="bazaar",
        aliases=["bz"],
        description="Browse the market stalls."
    )
    async def bazaar(self, ctx: commands.Context):
        """
        Open the interactive bazaar menu.
        
        Shows buttons for Apothecary, Provisioner, and Shady Dealer (Outcasts only).
        
        Usage: !bazaar or !bz
        """
        print(f"[DEBUG] shop.bazaar: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        user_bg = await get_user_stat(self.bot.db, ctx.author.id, "background") or "None"
        taels = await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0
        
        embed = bazaar_main_embed(taels)
        view = ShopView(ctx, user_bg)
        
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    
    # ==========================================
    # COMMAND: BUY
    # ==========================================
    
    @commands.hybrid_command(
        name="buy",
        description="Purchase an item. Usage: !buy <item name> [quantity]"
    )
    async def buy(self, ctx: commands.Context, *, args: str):
        """
        Purchase items from shops.
        
        Examples:
        - !buy Spirit Gathering Dan
        - !buy Spirit Gathering Dan 2
        - !buy "Spirit Gathering Dan" 2 (quotes optional)
        
        Large purchases (>500 Taels) require confirmation.
        """
        print(f"[DEBUG] shop.buy: {ctx.author.id} wants to buy {args}")
        
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        # Parse arguments
        parts = args.strip().split()
        if not parts:
            return await ctx.send(
                "❌ Please specify an item to buy. Example: `!buy Spirit Gathering Dan 2`",
                ephemeral=True
            )
        
        # Check if last part is a number (quantity)
        quantity = 1
        if parts[-1].isdigit():
            quantity = int(parts[-1])
            item_name = " ".join(parts[:-1])
        else:
            item_name = " ".join(parts)
        
        if not item_name:
            return await ctx.send(
                "❌ Please specify an item to buy. Example: `!buy Spirit Gathering Dan 2`",
                ephemeral=True
            )
        
        # Find item
        item = get_item_data(item_name)
        if not item:
            embed = item_not_for_sale_embed(item_name)
            return await ctx.send(embed=embed, ephemeral=True)
        
        item_key = item["key"]
        item_data = item["data"]
        price = item_data["price"]
        shop_name = item_data.get("shop", "Unknown")
        total_cost = price * quantity
        
        # Check shop access
        user_bg = await get_user_stat(self.bot.db, ctx.author.id, "background") or "None"
        can_access, error_msg = validate_shop_access(shop_name, user_bg)
        if not can_access:
            embed = shady_dealer_only_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Check Taels
        taels = await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0
        if taels < total_cost:
            embed = insufficient_taels_embed(total_cost, taels)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Large purchase confirmation
        if total_cost > 500:
            effect_preview = get_item_effect_preview(item_key)
            embed = purchase_confirmation_embed(item_key, quantity, total_cost, effect_preview)
            
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
            
            await ctx.send(embed=embed, view=view, ephemeral=True)
            return
        
        await self._process_buy(ctx, item_key, quantity, total_cost, shop_name)
    
    async def _process_buy(self, ctx, item_key: str, quantity: int, total_cost: int, shop_name: str):
        """Process the actual purchase after validation."""
        # Deduct Taels
        new_taels = (await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0) - total_cost
        await update_user_stat(self.bot.db, ctx.author.id, "taels", new_taels)
        
        is_bound = 1 if is_item_bound(item_key) else 0
        
        # Add item to inventory
        db = self.bot.db
        try:
            await db.inventory.update_one(
                {"user_id": ctx.author.id, "item_name": item_key},
                {"$inc": {"quantity": quantity}, "$set": {"bound": is_bound}},
                upsert=True
            )
        except Exception as e:
            print(f"[ERROR] shop._process_buy: {e}")
            await ctx.send("❌ An error occurred while processing your purchase. Please try again.", ephemeral=True)
            return
        
        embed = purchase_complete_embed(item_key, quantity, total_cost, shop_name, is_bound == 1)
        await ctx.send(embed=embed)
    
    # ==========================================
    # COMMAND: SEARCH
    # ==========================================
    
    @commands.hybrid_command(
        name="search",
        description="Find which shop sells an item."
    )
    async def search(self, ctx: commands.Context, *, item_name: str):
        """
        Search for an item across all shops.
        
        Shows price and which shop sells it.
        
        Usage: !search Spirit Gathering Dan
        """
        print(f"[DEBUG] shop.search: {ctx.author.id} searching for {item_name}")
        
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        results = search_items(item_name)
        
        embed = search_results_embed(item_name, results)
        await ctx.send(embed=embed, ephemeral=True)
    
    # ==========================================
    # COMMAND: INVENTORY
    # ==========================================
    
    @commands.hybrid_command(
        name="inventory",
        aliases=["inv"],
        description="View your items."
    )
    async def inventory(self, ctx: commands.Context):
        """
        View all items in your inventory.
        
        Shows item names, quantities, and bound status.
        
        Usage: !inventory or !inv
        """
        print(f"[DEBUG] shop.inventory: Called by {ctx.author.id}")
        
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        inv = await get_inventory(self.bot.db, ctx.author.id)
        taels = await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0
        
        embed = inventory_embed(ctx.author.name, taels, inv)
        await ctx.send(embed=embed)
    
    # ==========================================
    # COMMAND: USE
    # ==========================================
    
    @commands.hybrid_command(
        name="use",
        description="Consume an item from your inventory."
    )
    async def use(self, ctx: commands.Context, *, item_name: str):
        """
        Use a consumable item.
        
        Effects vary by item:
        - Spirit Gathering Dan: +20 Ki
        - Iron Bandage: +10 HP
        - Herbal Tea: +10 Vitality
        - etc.
        
        Usage: !use "Spirit Gathering Dan"
        """
        print(f"[DEBUG] shop.use: {ctx.author.id} using {item_name}")
        
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        # Find item in inventory
        inv = await get_inventory(self.bot.db, ctx.author.id)
        target_item = find_item_in_inventory(inv, item_name)
        
        if not target_item:
            embed = item_not_found_embed(item_name)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # FIXED: Using 'item_name' key (bug fix)
        item_key = target_item.get('item_name', target_item.get('name'))
        item_data = SHOP_ITEMS.get(item_key)
        
        if not item_data:
            return await ctx.send(f"❓ `{item_key}` has no known effect.", ephemeral=True)
        
        # Apply item effects
        db = self.bot.db
        user_id = ctx.author.id
        rank = await get_user_stat(db, user_id, "rank") or "The Bound (Mortal)"
        max_stats = get_max_stats(rank)
        effect = item_data.get("effect", {})
        
        ki = await get_user_stat(db, user_id, "ki") or 0
        hp = await get_user_stat(db, user_id, "hp") or 0
        vit = await get_user_stat(db, user_id, "vitality") or 0
        mastery = await get_user_stat(db, user_id, "mastery") or 0.0
        
        new_ki = ki
        new_hp = hp
        new_vit = vit
        new_mastery = mastery
        effect_msg = ""
        
        if "ki" in effect:
            new_ki = min(max_stats["ki_cap"], ki + effect["ki"])
            effect_msg += f"✨ +{effect['ki']} Ki. "
        if "hp" in effect:
            new_hp = max(1, hp + effect["hp"])
            effect_msg += f"🩸 {effect['hp']:+} HP. "
        if "vit" in effect:
            new_vit = min(max_stats["max_vit"], vit + effect["vit"])
            effect_msg += f"❤️ +{effect['vit']} Vitality. "
        if "vit_pct" in effect:
            gain = int(max_stats["max_vit"] * effect["vit_pct"])
            new_vit = min(max_stats["max_vit"], vit + gain)
            effect_msg += f"❤️ +{gain} Vitality ({int(effect['vit_pct']*100)}%). "
        if "mastery" in effect:
            new_mastery = min(100.0, mastery + effect["mastery"])
            effect_msg += f"📖 +{effect['mastery']}% Mastery. "
        
        await update_user_stat(db, user_id, "ki", new_ki)
        await update_user_stat(db, user_id, "hp", new_hp)
        await update_user_stat(db, user_id, "vitality", new_vit)
        await update_user_stat(db, user_id, "mastery", new_mastery)
        
        # Remove one item
        await remove_item(db, user_id, item_key, 1)
        
        embed = item_used_embed(item_key, effect_msg)
        await ctx.send(embed=embed)
    
    # ==========================================
    # COMMAND: SELL
    # ==========================================
    
    @commands.hybrid_command(
        name="sell",
        description="Sell an item for half its price. Usage: !sell <item> [quantity]"
    )
    async def sell(self, ctx: commands.Context, item_name: str, quantity: int = 1):
        """
        Sell items for half their original price.
        
        Bound items cannot be sold.
        
        Usage: !sell "Iron Bandage"
        !sell "Iron Bandage" 2
        """
        print(f"[DEBUG] shop.sell: {ctx.author.id} selling {quantity}x {item_name}")
        
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        # Find item in inventory
        inv = await get_inventory(self.bot.db, ctx.author.id)
        target_item = find_item_in_inventory(inv, item_name)
        
        if not target_item:
            embed = item_not_found_embed(item_name)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Check bound status
        if target_item.get('bound'):
            embed = cannot_sell_bound_item_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        
        # FIXED: Using 'item_name' key (bug fix)
        item_key = target_item.get('item_name', target_item.get('name'))
        available_qty = target_item.get('quantity', 0)
        
        if available_qty < quantity:
            embed = insufficient_quantity_embed(item_key, available_qty, quantity)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Calculate sell price
        sell_price = calculate_sell_price(item_key, quantity)
        if sell_price is None:
            return await ctx.send(f"❓ Cannot determine price for {item_key}.", ephemeral=True)
        
        # Add Taels and remove item
        new_taels = (await get_user_stat(self.bot.db, ctx.author.id, "taels") or 0) + sell_price
        await update_user_stat(self.bot.db, ctx.author.id, "taels", new_taels)
        await remove_item(self.bot.db, ctx.author.id, item_key, quantity)
        
        embed = item_sold_embed(item_key, quantity, sell_price)
        await ctx.send(embed=embed)
    
    # ==========================================
    # COMMAND: GIVE
    # ==========================================
    
        
    @commands.hybrid_command(name="give", description="Give an item to another player.")
    async def give(self, ctx, recipient: discord.Member, item_name: str, quantity: int = 1):
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        if await is_user_banned(self.bot.db, recipient.id):
            embed = cannot_give_to_banned_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        if recipient.id == ctx.author.id:
            embed = cannot_give_to_self_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        rank = await get_user_stat(self.bot.db, ctx.author.id, "rank") or "The Bound (Mortal)"
        if not can_give_items(rank):
            embed = rank_required_for_give_embed(get_rank_requirement_for_give())
            return await ctx.send(embed=embed, ephemeral=True)
        today = datetime.datetime.now().date().isoformat()
        give_date = await get_user_stat(self.bot.db, ctx.author.id, "daily_give_date")
        give_count = await get_user_stat(self.bot.db, ctx.author.id, "daily_give_count") or 0
        can_give, new_count = can_give_today(give_count, today, give_date)
        if not can_give:
            embed = give_limit_reached_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        on_cd, remaining = self.give_cooldowns.is_on_cooldown(ctx.author.id)
        if on_cd:
            embed = give_cooldown_embed(remaining)
            return await ctx.send(embed=embed, ephemeral=True)
        inv = await get_inventory(self.bot.db, ctx.author.id)
        target_item = find_item_in_inventory(inv, item_name)
        if not target_item:
            embed = item_not_found_embed(item_name)
            return await ctx.send(embed=embed, ephemeral=True)
        if target_item.get('bound'):
            embed = cannot_sell_bound_item_embed()
            return await ctx.send(embed=embed, ephemeral=True)
        item_key = target_item.get('item_name', target_item.get('name'))
        available_qty = target_item.get('quantity', 0)
        if available_qty < quantity:
            embed = insufficient_quantity_embed(item_key, available_qty, quantity)
            return await ctx.send(embed=embed, ephemeral=True)
        try:
            await remove_item(self.bot.db, ctx.author.id, item_key, quantity)
            for _ in range(quantity):
                await add_item(self.bot.db, recipient.id, item_key, 1, bound=False)
        except Exception as e:
            print(f"[ERROR] shop.give: {e}")
            await ctx.send("❌ An error occurred.", ephemeral=True)
            return
        if give_date != today:
            await update_user_stat(self.bot.db, ctx.author.id, "daily_give_date", today)
        await update_user_stat(self.bot.db, ctx.author.id, "daily_give_count", new_count + 1)
        self.give_cooldowns.set_cooldown(ctx.author.id)
        remaining_gives = get_daily_give_limit() - (new_count + 1)
        embed = item_given_embed(item_key, quantity, recipient, remaining_gives)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Shop(bot))
    print("[DEBUG] commands/shop.py: Setup complete")