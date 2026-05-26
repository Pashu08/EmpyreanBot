"""
backend/db.py - Database helper functions (standalone)
These functions wrap the MongoDBWrapper methods for easier importing.

All functions take a 'db' parameter which should be the MongoDBWrapper
instance from main.py (self.bot.db).

Usage example:
    from backend import db as db_utils
    user = await db_utils.fetch_user(ctx.bot.db, user_id)
"""

import datetime
from typing import Optional, Any

print("[DEBUG] db.py: Loading database helpers...")


# ==========================================
# USER HELPERS
# ==========================================

async def fetch_user(db, user_id: int) -> Optional[dict]:
    """Fetch a user's complete data document."""
    return await db.fetch_user(user_id)


async def user_exists(db, user_id: int) -> bool:
    """Check if a user exists in the database."""
    return await db.user_exists(user_id)


async def get_user_stat(db, user_id: int, stat_name: str) -> Any:
    """Get a single statistic from a user's document."""
    return await db.get_user_stat(user_id, stat_name)


async def update_user_stat(db, user_id: int, stat_name: str, value: Any):
    """Update a single statistic in a user's document."""
    await db.update_user_stat(user_id, stat_name, value)


# ==========================================
# INVENTORY HELPERS
# ==========================================

async def get_inventory(db, user_id: int) -> list:
    """Get all items in a user's inventory."""
    return await db.get_inventory(user_id)


async def add_item(db, user_id: int, item_name: str, quantity: int = 1, bound: bool = False):
    """Add an item to a user's inventory."""
    await db.add_item(user_id, item_name, quantity, bound)


async def update_item_name(db, user_id: int, old_name: str, new_name: str) -> bool:
    """Update an item's name (used for item mutation on breakthrough)."""
    return await db.update_item_name(user_id, old_name, new_name)


async def remove_item(db, user_id: int, item_name: str, quantity: int = 1) -> bool:
    """Remove a quantity of an item from a user's inventory."""
    return await db.remove_item(user_id, item_name, quantity)


async def has_item(db, user_id: int, item_name: str, quantity: int = 1) -> bool:
    """Check if a user has at least a certain quantity of an item."""
    return await db.has_item(user_id, item_name, quantity)


# ==========================================
# BOT SETTINGS HELPERS
# ==========================================

async def get_bot_setting(db, key: str, default: Any = None) -> Any:
    """Get a setting from the bot_settings collection."""
    return await db.get_bot_setting(key, default)


async def set_bot_setting(db, key: str, value: Any):
    """Set a setting in the bot_settings collection."""
    await db.set_bot_setting(key, value)


# ==========================================
# BANNED USERS HELPERS
# ==========================================

async def is_user_banned(db, user_id: int) -> bool:
    """Check if a user is banned from the bot."""
    return await db.is_user_banned(user_id)


async def ban_user(db, user_id: int, reason: str, banned_by: int):
    """Ban a user from using the bot."""
    await db.ban_user(user_id, reason, banned_by)


async def unban_user(db, user_id: int):
    """Unban a user."""
    await db.unban_user(user_id)


# ==========================================
# PERMISSION HELPERS
# ==========================================

async def get_user_permissions(db, user_id: int) -> list:
    """Get all permission strings for a user."""
    return await db.get_user_permissions(user_id)


async def add_user_permission(db, user_id: int, permission: str):
    """Grant a permission to a user."""
    await db.add_user_permission(user_id, permission)


async def remove_user_permission(db, user_id: int, permission: str):
    """Remove a permission from a user."""
    await db.remove_user_permission(user_id, permission)


# ==========================================
# USER COOLDOWNS HELPERS
# ==========================================

async def get_user_cooldown(db, cooldown_key: str) -> Optional[datetime.datetime]:
    """Get the last used timestamp for a cooldown key."""
    return await db.get_user_cooldown(cooldown_key)


async def set_user_cooldown(db, cooldown_key: str):
    """Set the current timestamp for a cooldown key."""
    await db.set_user_cooldown(cooldown_key)


print("[DEBUG] db.py: Database helpers loaded successfully")