"""
backend/permissions.py - Permission management for admin system

This module handles:
- Checking if a user has specific permissions
- Adding/removing permissions from users
- Managing Temporary God status (stored in database)
- Permission constants

The permission system has three levels:
1. Permanent God - Hardcoded user ID, bypasses all checks
2. Temporary God - Database-stored, full access to everything
3. Regular admins - Have specific permissions (player_manage, config_manage, system)

Uses admin_permissions collection (one document per permission)
"""

import datetime
from backend.constants import PERMANENT_GOD

print("[DEBUG] backend/permissions.py: Loading permission system...")

# ==========================================
# TEMPORARY GOD MANAGEMENT
# ==========================================

async def is_temp_god(bot, user_id: int) -> bool:
    """
    Check if a user is a Temporary God.

    Temporary Gods have full access to all admin commands,
    same as the Permanent God.
    """
    try:
        result = await bot.db.temp_gods.find_one({"user_id": user_id})
        return result is not None
    except Exception as e:
        print(f"[ERROR] is_temp_god failed for {user_id}: {e}")
        return False

async def add_temp_god(bot, user_id: int) -> bool:
    """
    Grant Temporary God status to a user.
    """
    try:
        if await is_temp_god(bot, user_id):
            return True

        await bot.db.temp_gods.insert_one({
            "user_id": user_id,
            "granted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        print(f"[DEBUG] add_temp_god: {user_id} promoted to Temporary God")
        return True
    except Exception as e:
        print(f"[ERROR] add_temp_god failed for {user_id}: {e}")
        return False

async def remove_temp_god(bot, user_id: int) -> bool:
    """
    Remove Temporary God status from a user.
    """
    try:
        result = await bot.db.temp_gods.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            print(f"[DEBUG] remove_temp_god: {user_id} demoted from Temporary God")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] remove_temp_god failed for {user_id}: {e}")
        return False

async def get_all_temp_gods(bot) -> list:
    """
    Get a list of all Temporary God user IDs.
    """
    try:
        cursor = bot.db.temp_gods.find({})
        return [doc["user_id"] async for doc in cursor]
    except Exception as e:
        print(f"[ERROR] get_all_temp_gods failed: {e}")
        return []

# ==========================================
# PERMISSION CHECKING (Using admin_permissions)
# ==========================================

async def has_permission(bot, user_id: int, permission: str) -> bool:
    """
    Check if a user has a specific permission.

    Permission check order (stops at first match):
    1. Permanent God (hardcoded) → ALWAYS True
    2. Temporary God (database) → ALWAYS True
    3. Database permission check → True if permission exists
    """
    # Level 1: Permanent God
    if user_id == PERMANENT_GOD:
        return True

    # Level 2: Temporary God
    if await is_temp_god(bot, user_id):
        return True

    # Level 3: Regular permission check from admin_permissions
    try:
        result = await bot.db.admin_permissions.find_one({
            "user_id": user_id,
            "permission": permission
        })
        return result is not None
    except Exception as e:
        print(f"[ERROR] has_permission failed for {user_id}, {permission}: {e}")
        return False

# ==========================================
# PERMISSION MANAGEMENT (Using admin_permissions)
# ==========================================

async def add_permission(bot, user_id: int, permission: str) -> bool:
    """
    Grant a specific permission to a user.
    """
    # Validate permission name
    if permission not in VALID_PERMISSIONS:
        print(f"[WARN] Invalid permission '{permission}' attempted for user {user_id}")
        return False

    try:
        # Check if already has the permission
        existing = await bot.db.admin_permissions.find_one({
            "user_id": user_id,
            "permission": permission
        })
        if existing:
            return True

        # Add the permission (one document per permission)
        await bot.db.admin_permissions.insert_one({
            "user_id": user_id,
            "permission": permission,
            "granted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        print(f"[DEBUG] add_permission: {user_id} granted {permission}")
        return True
    except Exception as e:
        print(f"[ERROR] add_permission failed for {user_id}, {permission}: {e}")
        return False

async def remove_permission(bot, user_id: int, permission: str) -> bool:
    """
    Remove a specific permission from a user.
    """
    # Validate permission name
    if permission not in VALID_PERMISSIONS:
        print(f"[WARN] Invalid permission '{permission}' attempted for user {user_id}")
        return False

    try:
        result = await bot.db.admin_permissions.delete_one({
            "user_id": user_id,
            "permission": permission
        })
        if result.deleted_count > 0:
            print(f"[DEBUG] remove_permission: {user_id} lost {permission}")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] remove_permission failed for {user_id}, {permission}: {e}")
        return False

async def get_user_permissions(bot, user_id: int) -> list:
    """
    Get all permissions for a user.
    """
    try:
        cursor = bot.db.admin_permissions.find({"user_id": user_id})
        docs = await cursor.to_list(length=10)
        return [doc["permission"] for doc in docs]
    except Exception as e:
        print(f"[ERROR] get_user_permissions failed for {user_id}: {e}")
        return []

async def set_user_permissions(bot, user_id: int, permissions: list) -> bool:
    """
    Replace all permissions for a user with a new list.

    WARNING: This deletes all existing permissions and adds new ones.
    """
    try:
        # Validate all permissions
        for perm in permissions:
            if perm not in VALID_PERMISSIONS:
                print(f"[WARN] Invalid permission '{perm}' in set_user_permissions")
                return False

        # Delete all existing permissions for this user
        await bot.db.admin_permissions.delete_many({"user_id": user_id})

        # Add new permissions
        for permission in permissions:
            await bot.db.admin_permissions.insert_one({
                "user_id": user_id,
                "permission": permission,
                "granted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })

        print(f"[DEBUG] set_user_permissions: {user_id} permissions set to {permissions}")
        return True
    except Exception as e:
        print(f"[ERROR] set_user_permissions failed for {user_id}: {e}")
        return False

# ==========================================
# PERMISSION CONSTANTS
# ==========================================

# Valid permission types that can be granted
VALID_PERMISSIONS = [
    "player_manage",   # Can reset players, set stats, fix meridians, refill
    "config_manage",   # Can toggle features, change cooldowns, set emojis/messages
    "system"           # Can sync commands, promote/demote, ban/unban
]

# Human-readable names for permissions (for display purposes)
PERMISSION_NAMES = {
    "player_manage": "👤 Player Management",
    "config_manage": "⚙️ Configuration Management",
    "system": "🔧 System Access"
}

# Descriptions for each permission (for help menus)
PERMISSION_DESCRIPTIONS = {
    "player_manage": "Reset players, modify stats, heal meridians, restore HP/Vitality",
    "config_manage": "Toggle features, change cooldowns, set custom emojis and messages",
    "system": "Sync slash commands, promote/demote gods, ban/unban users"
}

def get_permission_name(permission: str) -> str:
    """
    Get the human-readable name for a permission.
    """
    return PERMISSION_NAMES.get(permission, permission)

def get_permission_description(permission: str) -> str:
    """
    Get the description for a permission.
    """
    return PERMISSION_DESCRIPTIONS.get(permission, "No description available")

print("[DEBUG] backend/permissions.py: Permission system loaded successfully")
