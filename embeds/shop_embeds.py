"""
embeds/shop_embeds.py - Embed designs for Shop cog
Contains all embed builders for bazaar, inventory, buying, selling, and item management.

This file handles:
- Bazaar main menu embed
- Shop items listing embed (Apothecary, Provisioner, Shady Dealer)
- Inventory display embed
- Purchase confirmation and completion embeds
- Item use, sell, and give result embeds
- Search results embed
- Error embeds for shop system
"""

import discord
from backend.helpers import format_embed_color
from typing import List, Tuple, Optional

print("[DEBUG] shop_embeds.py: Loading shop embeds...")


# ==========================================
# BAZAAR MAIN MENU EMBED
# ==========================================

def bazaar_main_embed(taels: int) -> discord.Embed:
    """
    Build the main bazaar menu embed.
    
    Args:
        taels: User's current Taels
        
    Returns:
        discord.Embed: Formatted bazaar main menu
    """
    embed = discord.Embed(
        title="🏮 The Great Bazaar",
        description=f"💰 Your Taels: **{taels:,}**\n\nClick a button below to browse a shop.",
        color=format_embed_color("main")
    )
    embed.set_footer(text="Use `!buy <item> [quantity]` to purchase items directly.")
    
    return embed


# ==========================================
# SHOP ITEMS EMBED
# ==========================================

def shop_items_embed(
    shop_name: str,
    shop_emoji: str,
    taels: int,
    items: List[Tuple[str, int, str]]
) -> discord.Embed:
    """
    Build the embed showing items in a specific shop.
    
    Args:
        shop_name: Name of the shop (Apothecary, Provisioner, Shady Dealer)
        shop_emoji: Emoji for the shop
        taels: User's current Taels
        items: List of tuples (item_name, price, description)
        
    Returns:
        discord.Embed: Formatted shop items embed
    """
    embed = discord.Embed(
        title=f"{shop_emoji} {shop_name}",
        description=f"💰 Your Taels: **{taels:,}**\n\nUse `!buy <item> [quantity]` to purchase.\nExample: `!buy Spirit Gathering Dan 2`",
        color=format_embed_color("main")
    )
    
    for item_name, price, description in items[:10]:  # Max 10 items per page
        embed.add_field(
            name=f"{item_name} — {price:,} Taels",
            value=description[:100] if description else "No description",
            inline=False
        )
    
    if len(items) > 10:
        embed.set_footer(text=f"Showing 10 of {len(items)} items. Use !search to find specific items.")
    else:
        embed.set_footer(text="Click another button to browse different shops.")
    
    return embed


# ==========================================
# INVENTORY EMBED
# ==========================================

def inventory_embed(
    user_name: str,
    taels: int,
    items: List[dict],
    page: int = 0,
    items_per_page: int = 10
) -> discord.Embed:
    """
    Build the inventory embed with pagination support.
    
    Args:
        user_name: Name of the user
        taels: User's current Taels
        items: List of item dicts with keys: item_name, quantity, bound
        page: Current page number (0-indexed)
        items_per_page: Number of items per page (default 10)
        
    Returns:
        discord.Embed: Formatted inventory embed
    """
    total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(items))
    page_items = items[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🎒 Inventory: {user_name}",
        description=f"💰 Taels: {taels:,}",
        color=format_embed_color("main")
    )
    
    if not items:
        embed.description += "\n\n📭 Your inventory is empty."
        embed.set_footer(text="Use `!bazaar` to buy items or `!hunt` to find drops.")
        return embed
    
    for item in page_items:
        # FIXED: Using 'item_name' instead of 'name' (bug fix)
        item_name = item.get('item_name', 'Unknown')
        quantity = item.get('quantity', 0)
        is_bound = item.get('bound', False)
        
        bound_status = " 🔒 (bound)" if is_bound else ""
        embed.add_field(
            name=f"📦 {item_name}{bound_status}",
            value=f"Quantity: {quantity}",
            inline=True
        )
    
    # Add pagination info if multiple pages
    if total_pages > 1:
        embed.set_footer(text=f"Page {page + 1} of {total_pages} | Use !inventory to see all")
    
    return embed


# ==========================================
# PURCHASE CONFIRMATION EMBED
# ==========================================

def purchase_confirmation_embed(
    item_name: str,
    quantity: int,
    total_cost: int,
    effect_preview: str = None
) -> discord.Embed:
    """
    Build the confirmation embed for large purchases (>500 Taels).
    
    Args:
        item_name: Name of the item
        quantity: Number being purchased
        total_cost: Total cost in Taels
        effect_preview: Optional preview of item effect
        
    Returns:
        discord.Embed: Formatted confirmation embed
    """
    embed = discord.Embed(
        title="⚠️ Confirm Purchase",
        description=f"Are you sure you want to buy **{quantity}x {item_name}** for **{total_cost:,} Taels**?",
        color=format_embed_color("orange")
    )
    
    if effect_preview:
        embed.add_field(name="📜 Item Effect", value=effect_preview, inline=False)
    
    embed.set_footer(text="This action cannot be undone.")
    
    return embed


def purchase_complete_embed(
    item_name: str,
    quantity: int,
    total_cost: int,
    shop_name: str,
    is_bound: bool = False
) -> discord.Embed:
    """
    Build the success embed after a purchase.
    
    Args:
        item_name: Name of the item purchased
        quantity: Number purchased
        total_cost: Total cost in Taels
        shop_name: Which shop it was bought from
        is_bound: Whether the item is bound (cannot trade/sell)
        
    Returns:
        discord.Embed: Formatted purchase complete embed
    """
    embed = discord.Embed(
        title="🛍️ Purchase Complete",
        description=f"You bought **{quantity}x {item_name}** from the **{shop_name}** for **{total_cost:,} Taels**.",
        color=format_embed_color("win")
    )
    
    if is_bound:
        embed.add_field(
            name="📜 Bound Item",
            value="This item is bound to your soul and cannot be traded or sold.",
            inline=False
        )
    
    return embed


# ==========================================
# ITEM USE EMBED
# ==========================================

def item_used_embed(item_name: str, effect_message: str) -> discord.Embed:
    """
    Build the result embed after using an item.
    
    Args:
        item_name: Name of the item used
        effect_message: Description of what happened
        
    Returns:
        discord.Embed: Formatted item use embed
    """
    embed = discord.Embed(
        title="🎒 Item Used",
        description=f"You used **{item_name}**.\n\n{effect_message}",
        color=format_embed_color("win")
    )
    
    return embed


def item_not_found_embed(item_name: str) -> discord.Embed:
    """
    Build error embed when user doesn't have an item.
    
    Args:
        item_name: Name of the item not found
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Item Not Found",
        description=f"You don't have `{item_name}` in your inventory.",
        color=format_embed_color("error")
    )
    
    return embed


# ==========================================
# ITEM SELL EMBED
# ==========================================

def item_sold_embed(item_name: str, quantity: int, sell_price: int) -> discord.Embed:
    """
    Build the result embed after selling an item.
    
    Args:
        item_name: Name of the item sold
        quantity: Number sold
        sell_price: Total Taels received
        
    Returns:
        discord.Embed: Formatted sell result embed
    """
    embed = discord.Embed(
        title="💰 Item Sold",
        description=f"You sold **{quantity}x {item_name}** for **{sell_price:,} Taels**.",
        color=format_embed_color("gold")
    )
    
    return embed


def cannot_sell_bound_item_embed() -> discord.Embed:
    """
    Build error embed when trying to sell a bound item.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Cannot Sell",
        description="Bound items are soul-bound and cannot be sold to merchants.",
        color=format_embed_color("error")
    )
    
    return embed


def insufficient_quantity_embed(item_name: str, available: int, requested: int) -> discord.Embed:
    """
    Build error embed when trying to sell/use more items than owned.
    
    Args:
        item_name: Name of the item
        available: Quantity available
        requested: Quantity requested
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Insufficient Quantity",
        description=f"You only have **{available}** of `{item_name}`, but tried to use/sell **{requested}**.",
        color=format_embed_color("error")
    )
    
    return embed


# ==========================================
# ITEM GIVE EMBED
# ==========================================

def item_given_embed(
    item_name: str,
    quantity: int,
    recipient: discord.Member,
    remaining_gives: int
) -> discord.Embed:
    """
    Build the result embed after giving an item.
    
    Args:
        item_name: Name of the item given
        quantity: Number given
        recipient: The user who received the item
        remaining_gives: How many more gives available today
        
    Returns:
        discord.Embed: Formatted give result embed
    """
    embed = discord.Embed(
        title="🎁 Item Given",
        description=f"You gave **{quantity}x {item_name}** to {recipient.mention}.",
        color=format_embed_color("win")
    )
    embed.set_footer(text=f"You have {remaining_gives} gives remaining today.")
    
    return embed


def give_limit_reached_embed() -> discord.Embed:
    """
    Build error embed when user has reached daily give limit.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Give Limit Reached",
        description="You have reached your daily give limit (3). Try again tomorrow.",
        color=format_embed_color("error")
    )
    
    return embed


def give_cooldown_embed(remaining_seconds: int) -> discord.Embed:
    """
    Build error embed for give command cooldown.
    
    Args:
        remaining_seconds: Seconds remaining on cooldown
        
    Returns:
        discord.Embed: Formatted cooldown embed
    """
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    
    if minutes > 0:
        time_text = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
    else:
        time_text = f"{seconds} second{'s' if seconds != 1 else ''}"
    
    embed = discord.Embed(
        title="⏳ Cooldown",
        description=f"Please wait **{time_text}** before using `!give` again.",
        color=format_embed_color("orange")
    )
    
    return embed


def cannot_give_to_self_embed() -> discord.Embed:
    """
    Build error embed when trying to give an item to yourself.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Cannot Give to Self",
        description="You cannot give items to yourself. Find a worthy cultivator instead.",
        color=format_embed_color("error")
    )
    
    return embed


def cannot_give_to_banned_embed() -> discord.Embed:
    """
    Build error embed when trying to give an item to a banned user.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Cannot Give",
        description="You cannot give items to a banned user.",
        color=format_embed_color("error")
    )
    
    return embed


def rank_required_for_give_embed(required_rank: str = "Third-Rate Warrior") -> discord.Embed:
    """
    Build error embed when user doesn't have high enough rank to give items.
    
    Args:
        required_rank: Rank required to give items
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Rank Required",
        description=f"You must be at least **{required_rank}** to give items to others.",
        color=format_embed_color("error")
    )
    
    return embed


# ==========================================
# SEARCH RESULTS EMBED
# ==========================================

def search_results_embed(query: str, results: List[Tuple[str, int, str]]) -> discord.Embed:
    """
    Build the search results embed.
    
    Args:
        query: The search term
        results: List of tuples (item_name, price, shop_name)
        
    Returns:
        discord.Embed: Formatted search results embed
    """
    if not results:
        embed = discord.Embed(
            title=f"🔍 Search Results",
            description=f"No items found matching `{query}`.",
            color=format_embed_color("error")
        )
        return embed
    
    description = "\n".join([
        f"**{item_name}** – {price:,} Taels ({shop_name})"
        for item_name, price, shop_name in results[:10]
    ])
    
    embed = discord.Embed(
        title=f"🔍 Search results for '{query}'",
        description=description,
        color=format_embed_color("teal")
    )
    
    if len(results) > 10:
        embed.set_footer(text=f"Showing 10 of {len(results)} results.")
    
    return embed


# ==========================================
# POUCH EMBED
# ==========================================

def pouch_embed(taels: int) -> discord.Embed:
    """
    Build the pouch embed showing user's Taels.
    
    Args:
        taels: User's current Taels
        
    Returns:
        discord.Embed: Formatted pouch embed
    """
    embed = discord.Embed(
        title="💰 Your Pouch",
        description=f"You have **{taels:,} Taels**.",
        color=format_embed_color("gold")
    )
    embed.set_footer(text="Use `!work` to earn more Taels, or `!bazaar` to spend them.")
    
    return embed


# ==========================================
# ERROR EMBEDS
# ==========================================

def shop_feature_disabled_embed() -> discord.Embed:
    """
    Build error embed when shop feature is disabled.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Market Closed",
        description="The Bazaar is currently closed by the merchant guild.",
        color=format_embed_color("error")
    )
    
    return embed


def item_not_for_sale_embed(item_name: str) -> discord.Embed:
    """
    Build error embed when an item doesn't exist in any shop.
    
    Args:
        item_name: Name of the item not found
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Item Not Found",
        description=f"`{item_name}` is not sold in any shop. Use `!search` to check available items.",
        color=format_embed_color("error")
    )
    
    return embed


def shady_dealer_only_embed() -> discord.Embed:
    """
    Build error embed when non-Outcast tries to buy from Shady Dealer.
    
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Shady Dealer",
        description="Only **Outcasts** can buy from the Shady Dealer. The merchant eyes you suspiciously.",
        color=format_embed_color("error")
    )
    
    return embed


def insufficient_taels_embed(required: int, current: int) -> discord.Embed:
    """
    Build error embed when user doesn't have enough Taels.
    
    Args:
        required: Taels required
        current: Current Taels
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Insufficient Taels",
        description=f"You need **{required:,} Taels** (you have {current:,}).",
        color=format_embed_color("error")
    )
    
    return embed


def shop_no_items_embed(shop_name: str) -> discord.Embed:
    """
    Build error embed when a shop has no items.
    
    Args:
        shop_name: Name of the shop
        
    Returns:
        discord.Embed: Formatted error embed
    """
    embed = discord.Embed(
        title="❌ Empty Shop",
        description=f"{shop_name} has no items available at this time.",
        color=format_embed_color("error")
    )
    
    return embed


print("[DEBUG] shop_embeds.py: Shop embeds loaded successfully")