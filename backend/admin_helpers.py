"""
backend/admin_helpers.py - Admin helper functions for logging and utilities
"""

import discord
from embeds.admin_embeds import admin_log_embed
import config

print("[DEBUG] backend/admin_helpers.py: Loading admin helpers...")

async def log_admin_command(bot, ctx, command_name: str, details: str = ""):
    """Log an admin command to the configured admin log channel."""
    if not config.ADMIN_LOG_CHANNEL_ID:
        return
    
    channel = bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
    if not channel:
        return
    
    embed = admin_log_embed(command_name, ctx.author, ctx.channel, details)
    await channel.send(embed=embed)

async def can_use_admin_command(bot, user_id: int, permission: str = None) -> bool:
    """Check if a user can use an admin command."""
    from backend.permissions import has_permission
    from backend.constants import PERMANENT_GOD
    
    if user_id == PERMANENT_GOD:
        return True
    
    if permission:
        return await has_permission(bot, user_id, permission)
    
    return False

# ==========================================
# NEW FUNCTION FOR ADMIN INVENTORY INSPECT
# ==========================================

async def format_inventory_for_admin(inventory_items: list) -> str:
    """
    Format inventory items for admin display.
    
    Args:
        inventory_items: List of item dicts from database
        
    Returns:
        str: Formatted string of items with quantities
    """
    if not inventory_items:
        return "📭 No items in inventory"
    
    items_list = []
    for item in inventory_items:
        item_name = item.get("item_name", "Unknown")
        quantity = item.get("quantity", 0)
        is_bound = "🔒" if item.get("bound") else "📦"
        items_list.append(f"{is_bound} {item_name}: {quantity}")
    
    return "\n".join(items_list)

print("[DEBUG] backend/admin_helpers.py: Admin helpers loaded successfully")
