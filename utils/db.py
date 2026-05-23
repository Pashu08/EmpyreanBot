from typing import Optional, Any
import datetime

print("[DEBUG] db.py: Loading database helpers...")

# ==========================================
# NOTE: This file now works with MongoDB through the MongoDBWrapper
# The 'db' parameter passed to these functions should be the MongoDBWrapper
# instance from main.py (self.bot.db)
# ==========================================

# ==========================================
# USER HELPERS
# ==========================================

async def fetch_user(db, user_id: int) -> Optional[dict]:
    """Returns full user row as a dict, or None if not registered."""
    print(f"[DEBUG] db.fetch_user: user_id={user_id}")
    user = await db.fetch_user(user_id)
    if user:
        print(f"[DEBUG] db.fetch_user: Found user {user_id}")
    else:
        print(f"[DEBUG] db.fetch_user: No user found for {user_id}")
    return user

async def user_exists(db, user_id: int) -> bool:
    print(f"[DEBUG] db.user_exists: user_id={user_id}")
    exists = await db.user_exists(user_id)
    print(f"[DEBUG] db.user_exists: {exists}")
    return exists

async def get_user_stat(db, user_id: int, stat_name: str) -> Any:
    """Get a single stat from a user."""
    print(f"[DEBUG] db.get_user_stat: user_id={user_id}, stat={stat_name}")
    user = await db.fetch_user(user_id)
    value = user.get(stat_name) if user else None
    print(f"[DEBUG] db.get_user_stat: value={value}")
    return value

async def update_user_stat(db, user_id: int, stat_name: str, value: Any):
    """Update a single stat for a user."""
    print(f"[DEBUG] db.update_user_stat: user_id={user_id}, stat={stat_name}, value={value}")
    await db.update_user(user_id, {stat_name: value})
    print(f"[DEBUG] db.update_user_stat: Updated")

# ==========================================
# INVENTORY HELPERS
# ==========================================

async def get_inventory(db, user_id: int) -> list[dict]:
    """Returns list of {name, quantity, bound} dicts."""
    print(f"[DEBUG] db.get_inventory: user_id={user_id}")
    result = await db.get_inventory(user_id)
    print(f"[DEBUG] db.get_inventory: Found {len(result)} items")
    return result

async def add_item(db, user_id: int, item_name: str, qty: int = 1, bound: bool = False):
    """Add an item to inventory. bound=True makes it non-tradeable/non-sellable."""
    print(f"[DEBUG] db.add_item: user_id={user_id}, item={item_name}, qty={qty}, bound={bound}")
    await db.add_item(user_id, item_name, qty, bound)
    print(f"[DEBUG] db.add_item: Added/updated")

async def update_item_name(db, user_id: int, old_name: str, new_name: str):
    """Update an item's name (used for item mutation on breakthrough)."""
    print(f"[DEBUG] db.update_item_name: user_id={user_id}, {old_name} -> {new_name}")
    # This requires a custom method in MongoDBWrapper
    # Fetch the item
    item = await db.inventory.find_one({"user_id": user_id, "item_name": old_name})
    if not item:
        print(f"[DEBUG] db.update_item_name: Item not found in inventory")
        return False
    
    quantity = item.get("quantity", 1)
    bound = item.get("bound", 0)
    
    # Delete old, insert new
    await db.inventory.delete_one({"user_id": user_id, "item_name": old_name})
    await db.inventory.insert_one({
        "user_id": user_id,
        "item_name": new_name,
        "quantity": quantity,
        "bound": bound
    })
    print(f"[DEBUG] db.update_item_name: Successfully updated")
    return True

async def remove_item(db, user_id: int, item_name: str, qty: int = 1) -> bool:
    """Returns False if player doesn't have enough."""
    print(f"[DEBUG] db.remove_item: user_id={user_id}, item={item_name}, qty={qty}")
    result = await db.remove_item(user_id, item_name, qty)
    print(f"[DEBUG] db.remove_item: {'Success' if result else 'Not enough items'}")
    return result

async def has_item(db, user_id: int, item_name: str, qty: int = 1) -> bool:
    """Check if user has at least qty of an item."""
    print(f"[DEBUG] db.has_item: user_id={user_id}, item={item_name}, qty={qty}")
    result = await db.has_item(user_id, item_name, qty)
    print(f"[DEBUG] db.has_item: {result}")
    return result

# ==========================================
# ADMIN HELPERS (for the admins table)
# ==========================================
# Note: The admins table is separate from admin_permissions
# This is for legacy !admin commands

async def get_admins(db) -> set[int]:
    """Get all user IDs from the admins collection."""
    print(f"[DEBUG] db.get_admins: Fetching all admins")
    cursor = db.db.admins.find({})
    admins = await cursor.to_list(length=100)
    result = {admin["user_id"] for admin in admins}
    print(f"[DEBUG] db.get_admins: Found {len(result)} admins")
    return result

async def add_admin(db, user_id: int):
    """Add a user to the admins collection."""
    print(f"[DEBUG] db.add_admin: user_id={user_id}")
    await db.db.admins.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )
    print(f"[DEBUG] db.add_admin: Added")

async def remove_admin(db, user_id: int):
    """Remove a user from the admins collection."""
    print(f"[DEBUG] db.remove_admin: user_id={user_id}")
    await db.db.admins.delete_one({"user_id": user_id})
    print(f"[DEBUG] db.remove_admin: Removed")

# ==========================================
# BOT SETTINGS HELPERS
# ==========================================

async def get_bot_setting(db, key: str, default: Any = None) -> Any:
    """Get a setting from bot_settings collection."""
    print(f"[DEBUG] db.get_bot_setting: key={key}")
    value = await db.get_bot_setting(key, default)
    print(f"[DEBUG] db.get_bot_setting: returning {value}")
    return value

async def set_bot_setting(db, key: str, value: Any):
    """Set a setting in bot_settings collection."""
    print(f"[DEBUG] db.set_bot_setting: key={key}, value={value}")
    await db.set_bot_setting(key, value)
    print(f"[DEBUG] db.set_bot_setting: Saved")

# ==========================================
# BANNED USERS HELPERS
# ==========================================

async def is_user_banned(db, user_id: int) -> bool:
    """Check if a user is banned."""
    print(f"[DEBUG] db.is_user_banned: user_id={user_id}")
    banned = await db.is_user_banned(user_id)
    print(f"[DEBUG] db.is_user_banned: {banned}")
    return banned

async def ban_user(db, user_id: int, reason: str, banned_by: int):
    """Ban a user."""
    print(f"[DEBUG] db.ban_user: user_id={user_id}, reason={reason}, by={banned_by}")
    await db.ban_user(user_id, reason, banned_by)
    print(f"[DEBUG] db.ban_user: Banned")

async def unban_user(db, user_id: int):
    """Unban a user."""
    print(f"[DEBUG] db.unban_user: user_id={user_id}")
    await db.unban_user(user_id)
    print(f"[DEBUG] db.unban_user: Unbanned")

# ==========================================
# PERMISSION HELPERS
# ==========================================

async def get_user_permissions(db, user_id: int) -> list[str]:
    """Get all permission strings for a user."""
    print(f"[DEBUG] db.get_user_permissions: user_id={user_id}")
    perms = await db.get_user_permissions(user_id)
    print(f"[DEBUG] db.get_user_permissions: {perms}")
    return perms

async def add_user_permission(db, user_id: int, permission: str):
    """Grant a permission to a user."""
    print(f"[DEBUG] db.add_user_permission: user_id={user_id}, perm={permission}")
    await db.add_user_permission(user_id, permission)
    print(f"[DEBUG] db.add_user_permission: Added")

async def remove_user_permission(db, user_id: int, permission: str):
    """Remove a permission from a user."""
    print(f"[DEBUG] db.remove_user_permission: user_id={user_id}, perm={permission}")
    await db.remove_user_permission(user_id, permission)
    print(f"[DEBUG] db.remove_user_permission: Removed")

# ==========================================
# USER COOLDOWNS HELPERS
# ==========================================

async def get_user_cooldown(db, cooldown_key: str) -> Optional[datetime.datetime]:
    """Get last used timestamp for a cooldown key."""
    print(f"[DEBUG] db.get_user_cooldown: key={cooldown_key}")
    dt = await db.get_user_cooldown(cooldown_key)
    print(f"[DEBUG] db.get_user_cooldown: found {dt}" if dt else f"[DEBUG] db.get_user_cooldown: not found")
    return dt

async def set_user_cooldown(db, cooldown_key: str):
    """Set the current timestamp for a cooldown key."""
    print(f"[DEBUG] db.set_user_cooldown: key={cooldown_key}")
    await db.set_user_cooldown(cooldown_key)
    print(f"[DEBUG] db.set_user_cooldown: Saved")

print("[DEBUG] db.py: Database helpers loaded successfully")