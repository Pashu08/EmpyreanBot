"""
backend/shop_helpers.py - Helper functions and UI views for Shop cog

This module handles:
- ShopView and ShopButton classes (interactive shop buttons)
- GiveCooldownManager class (cooldown tracking for !give command)
- Item validation and price calculation helpers
- Shop access checking (Shady Dealer only for Outcasts)
- Purchase helpers (effect preview, bound item detection)
"""

import discord
from discord.ui import View, Button
import datetime
from typing import List, Tuple, Optional, Dict, Any

from backend.constants import SHOP_ITEMS
from embeds.shop_embeds import shop_items_embed, shop_no_items_embed

print("[DEBUG] shop_helpers.py: Loading shop helpers...")


# ==========================================
# SHOP DATA CONSTANTS
# ==========================================

# Shop display information
SHOP_INFO = {
    "Apothecary": {
        "emoji": "💊",
        "description": "Pills, elixirs, and medicinal concoctions",
        "require_outcast": False
    },
    "Provisioner": {
        "emoji": "🍱",
        "description": "Food, supplies, and daily necessities",
        "require_outcast": False
    },
    "Shady Dealer": {
        "emoji": "👺",
        "description": "Forbidden goods and rare treasures",
        "require_outcast": True
    }
}


# ==========================================
# GIVE COOLDOWN MANAGER
# ==========================================

class GiveCooldownManager:
    """
    Manages 5-minute cooldowns for the !give command.
    Prevents players from spamming item transfers.
    """
    
    def __init__(self):
        """Initialize empty cooldown dictionary."""
        self._cooldowns: Dict[int, datetime.datetime] = {}
    
    def is_on_cooldown(self, user_id: int) -> Tuple[bool, int]:
        """
        Check if a user is on cooldown for giving items.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple[bool, int]: (is_on_cooldown, remaining_seconds)
        """
        cooldown_until = self._cooldowns.get(user_id)
        if not cooldown_until:
            return False, 0
        
        now = datetime.datetime.now()
        if now >= cooldown_until:
            # Cooldown expired, clean up
            del self._cooldowns[user_id]
            return False, 0
        
        remaining = int((cooldown_until - now).total_seconds())
        return True, remaining
    
    def set_cooldown(self, user_id: int, duration_seconds: int = 300):
        """
        Set a cooldown for a user (default 5 minutes).
        
        Args:
            user_id: Discord user ID
            duration_seconds: Cooldown duration (default 300 seconds = 5 minutes)
        """
        self._cooldowns[user_id] = datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds)
    
    def clear_cooldown(self, user_id: int):
        """Manually clear a user's cooldown."""
        self._cooldowns.pop(user_id, None)


# ==========================================
# SHOP BUTTON (Individual shop button)
# ==========================================

class ShopButton(Button):
    """
    Button for a specific shop in the bazaar.
    When clicked, shows items from that shop.
    """
    
    def __init__(self, shop_name: str, emoji: str, style: discord.ButtonStyle):
        """
        Initialize a shop button.
        
        Args:
            shop_name: Name of the shop (Apothecary, Provisioner, Shady Dealer)
            emoji: Emoji to display on the button
            style: Button style (primary, secondary, danger, etc.)
        """
        super().__init__(label=shop_name, emoji=emoji, style=style, custom_id=shop_name)
        self.shop_name = shop_name
    
    async def callback(self, interaction: discord.Interaction):
        """
        Handle button click - show items from this shop.
        """
        # Verify it's the same user
        if interaction.user.id != self.view.ctx.author.id:
            await interaction.response.send_message(
                "❌ This bazaar stall is not meant for you.",
                ephemeral=True
            )
            return
        
        # Get items from this shop
        items = []
        for item_name, data in SHOP_ITEMS.items():
            if data.get("shop") == self.shop_name:
                items.append((item_name, data["price"], data.get("desc", "No description")))
        
        if not items:
            embed = shop_no_items_embed(self.shop_name)
            await interaction.response.edit_message(embed=embed, view=self.view)
            return
        
        # Get user's Taels
        from backend.db import get_user_stat
        taels = await get_user_stat(interaction.client.db, interaction.user.id, "taels") or 0
        
        # Get shop info
        shop_info = SHOP_INFO.get(self.shop_name, {})
        shop_emoji = shop_info.get("emoji", "🏪")
        
        # Send shop items embed
        embed = shop_items_embed(
            shop_name=self.shop_name,
            shop_emoji=shop_emoji,
            taels=taels,
            items=items
        )
        
        await interaction.response.edit_message(embed=embed, view=self.view)


# ==========================================
# SHOP VIEW (Container for all shop buttons)
# ==========================================

class ShopView(View):
    """
    View containing all shop buttons.
    Dynamically shows Shady Dealer only for Outcast background.
    """
    
    def __init__(self, ctx, user_background: str):
        """
        Initialize the shop view.
        
        Args:
            ctx: Command context
            user_background: User's background (Laborer, Outcast, Hermit)
        """
        super().__init__(timeout=60)
        self.ctx = ctx
        
        # Always add Apothecary and Provisioner
        self.add_item(ShopButton("Apothecary", "💊", discord.ButtonStyle.primary))
        self.add_item(ShopButton("Provisioner", "🍱", discord.ButtonStyle.primary))
        
        # Only add Shady Dealer for Outcasts
        if user_background == "Outcast":
            self.add_item(ShopButton("Shady Dealer", "👺", discord.ButtonStyle.danger))
    
    async def on_timeout(self):
        """Handle view timeout - disable all buttons."""
        for child in self.children:
            child.disabled = True
        
        if hasattr(self, 'message'):
            try:
                embed = discord.Embed(
                    title="⏳ Bazaar Closed",
                    description="The market stalls have closed due to inactivity. Type `!bazaar` to open again.",
                    color=0xE74C3C
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass


# ==========================================
# ITEM VALIDATION HELPERS
# ==========================================

def get_item_data(item_name: str) -> Optional[Dict[str, Any]]:
    """
    Get data for an item by name (case-insensitive).
    
    Args:
        item_name: Name of the item to look up
        
    Returns:
        Optional[Dict]: Item data dict, or None if not found
    """
    for key, data in SHOP_ITEMS.items():
        if key.lower() == item_name.lower():
            return {"key": key, "data": data}
    return None


def get_item_price(item_name: str) -> Optional[int]:
    """
    Get the price of an item.
    
    Args:
        item_name: Name of the item
        
    Returns:
        Optional[int]: Price in Taels, or None if not found
    """
    item = get_item_data(item_name)
    if item:
        return item["data"].get("price")
    return None


def get_item_shop(item_name: str) -> Optional[str]:
    """
    Get which shop sells an item.
    
    Args:
        item_name: Name of the item
        
    Returns:
        Optional[str]: Shop name, or None if not found
    """
    item = get_item_data(item_name)
    if item:
        return item["data"].get("shop")
    return None


def calculate_sell_price(item_name: str, quantity: int) -> Optional[int]:
    """
    Calculate how many Taels you get for selling an item (50% of buy price).
    
    Args:
        item_name: Name of the item
        quantity: Number of items to sell
        
    Returns:
        Optional[int]: Total sell price, or None if item not found
    """
    price = get_item_price(item_name)
    if price is None:
        return None
    
    sell_price = int(price * quantity * 0.5)
    return max(1, sell_price)  # Minimum 1 Tael


def is_item_bound(item_name: str) -> bool:
    """
    Check if an item is bound (cannot be sold or given away).
    
    Args:
        item_name: Name of the item
        
    Returns:
        bool: True if bound, False otherwise
    """
    # Blood-Burning Catalyst is bound
    bound_items = ["Blood-Burning Catalyst"]
    return item_name in bound_items


def can_access_shady_dealer(user_background: str) -> bool:
    """
    Check if a user can access the Shady Dealer.
    
    Args:
        user_background: User's background (Laborer, Outcast, Hermit)
        
    Returns:
        bool: True if user is Outcast, False otherwise
    """
    return user_background == "Outcast"


def validate_shop_access(shop_name: str, user_background: str) -> Tuple[bool, str]:
    """
    Validate if a user can access a specific shop.
    
    Args:
        shop_name: Name of the shop
        user_background: User's background
        
    Returns:
        Tuple[bool, str]: (can_access, error_message)
    """
    if shop_name == "Shady Dealer" and user_background != "Outcast":
        return False, "Only **Outcasts** can buy from the Shady Dealer."
    return True, None


# ==========================================
# PURCHASE HELPERS
# ==========================================

def get_item_effect_preview(item_name: str) -> str:
    """
    Get a preview of an item's effect for confirmation embeds.
    
    Args:
        item_name: Name of the item
        
    Returns:
        str: Preview text of item effect
    """
    item = get_item_data(item_name)
    if not item:
        return "Unknown effect."
    
    effect = item["data"].get("effect", {})
    effect_parts = []
    
    if "ki" in effect:
        effect_parts.append(f"✨ Restores {effect['ki']} Ki")
    if "hp" in effect:
        val = effect['hp']
        if val > 0:
            effect_parts.append(f"🩸 Restores {val} HP")
        else:
            effect_parts.append(f"💀 Deals {abs(val)} damage")
    if "vit" in effect:
        effect_parts.append(f"❤️ Restores {effect['vit']} Vitality")
    if "vit_pct" in effect:
        effect_parts.append(f"❤️ Restores {int(effect['vit_pct']*100)}% of max Vitality")
    if "mastery" in effect:
        effect_parts.append(f"📖 Increases Mastery by {effect['mastery']}%")
    
    if effect_parts:
        return "\n".join(effect_parts)
    return "No special effect."


def calculate_total_cost(item_name: str, quantity: int) -> Optional[int]:
    """
    Calculate total cost for buying a quantity of an item.
    
    Args:
        item_name: Name of the item
        quantity: Number to buy
        
    Returns:
        Optional[int]: Total cost, or None if item not found
    """
    price = get_item_price(item_name)
    if price is None:
        return None
    return price * quantity


# ==========================================
# INVENTORY HELPERS
# ==========================================

def format_inventory_item(item: dict) -> dict:
    """
    Format an inventory item for display, ensuring correct key names.
    
    Args:
        item: Raw inventory item from database
        
    Returns:
        dict: Formatted item with consistent keys
    """
    return {
        "item_name": item.get("item_name", item.get("name", "Unknown")),
        "quantity": item.get("quantity", 0),
        "bound": item.get("bound", False)
    }


def find_item_in_inventory(inventory: List[dict], item_name: str) -> Optional[dict]:
    """
    Find an item in inventory by name (case-insensitive).
    
    Args:
        inventory: List of inventory items
        item_name: Name of the item to find
        
    Returns:
        Optional[dict]: Item dict if found, None otherwise
    """
    for item in inventory:
        # FIXED: Using 'item_name' key (bug fix)
        inv_name = item.get("item_name", item.get("name", ""))
        if inv_name.lower() == item_name.lower():
            return item
    return None


# ==========================================
# SEARCH HELPERS
# ==========================================

def search_items(query: str) -> List[Tuple[str, int, str]]:
    """
    Search for items matching a query (case-insensitive partial match).
    
    Args:
        query: Search term
        
    Returns:
        List[Tuple[str, int, str]]: List of (item_name, price, shop_name)
    """
    results = []
    query_lower = query.lower()
    
    for item_name, data in SHOP_ITEMS.items():
        if query_lower in item_name.lower():
            price = data.get("price", 0)
            shop = data.get("shop", "Unknown")
            results.append((item_name, price, shop))
    
    return results


# ==========================================
# RANK VALIDATION FOR GIVE
# ==========================================

def can_give_items(rank: str) -> bool:
    """
    Check if a user's rank is high enough to give items.
    
    Args:
        rank: User's cultivation rank
        
    Returns:
        bool: True if rank is Third-Rate Warrior or higher
    """
    valid_ranks = ["Third-Rate Warrior", "Second-Rate Warrior", "First-Rate Warrior", "Peak Master"]
    return any(r in rank for r in valid_ranks)


def get_rank_requirement_for_give() -> str:
    """
    Get the rank requirement for giving items.
    
    Returns:
        str: Required rank name
    """
    return "Third-Rate Warrior"


# ==========================================
# DAILY GIVE LIMIT HELPERS
# ==========================================

def get_daily_give_limit() -> int:
    """
    Get the maximum number of give actions allowed per day.
    
    Returns:
        int: Daily give limit (3)
    """
    return 3


def can_give_today(give_count: int, today_date: str, last_date: str) -> Tuple[bool, int]:
    """
    Check if user can still give items today and reset count if needed.
    
    Args:
        give_count: Current give count from database
        today_date: Today's date in ISO format
        last_date: Last recorded give date from database
        
    Returns:
        Tuple[bool, int]: (can_give, new_count)
    """
    if last_date != today_date:
        # New day, reset count
        return True, 0
    
    # Same day, check limit
    limit = get_daily_give_limit()
    return give_count < limit, give_count


print("[DEBUG] shop_helpers.py: Shop helpers loaded successfully")