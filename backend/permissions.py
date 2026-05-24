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
"""

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
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to check
        
    Returns:
        bool: True if user is a Temporary God, False otherwise
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
    
    Temporary Gods have all permissions and bypass all checks.
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to promote
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if already a temp god
        if await is_temp_god(bot, user_id):
            return True
        
        await bot.db.temp_gods.insert_one({
            "user_id": user_id,
            "granted_at": __import__('datetime').datetime.now().isoformat()
        })
        print(f"[DEBUG] add_temp_god: {user_id} promoted to Temporary God")
        return True
    except Exception as e:
        print(f"[ERROR] add_temp_god failed for {user_id}: {e}")
        return False


async def remove_temp_god(bot, user_id: int) -> bool:
    """
    Remove Temporary God status from a user.
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to demote
        
    Returns:
        bool: True if successful, False otherwise
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
    
    Args:
        bot: The bot instance (for database access)
        
    Returns:
        list: List of user IDs that have Temporary God status
    """
    try:
        cursor = bot.db.temp_gods.find({})
        return [doc["user_id"] async for doc in cursor]
    except Exception as e:
        print(f"[ERROR] get_all_temp_gods failed: {e}")
        return []


# ==========================================
# PERMISSION CHECKING
# ==========================================

async def has_permission(bot, user_id: int, permission: str) -> bool:
    """
    Check if a user has a specific permission.
    
    Permission check order (stops at first match):
    1. Permanent God (hardcoded) → ALWAYS True
    2. Temporary God (database) → ALWAYS True
    3. Database permission check → True if permission exists
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to check
        permission: Permission to check (player_manage, config_manage, system)
        
    Returns:
        bool: True if user has the permission, False otherwise
    """
    # Level 1: Permanent God (hardcoded, always has access)
    if user_id == PERMANENT_GOD:
        return True
    
    # Level 2: Temporary God (database-stored, full access)
    if await is_temp_god(bot, user_id):
        return True
    
    # Level 3: Regular permission check from database
    try:
        perms = await get_user_permissions(bot, user_id)
        return permission in perms
    except Exception as e:
        print(f"[ERROR] has_permission failed for {user_id}, {permission}: {e}")
        return False


# ==========================================
# PERMISSION MANAGEMENT (CRUD)
# ==========================================

async def add_permission(bot, user_id: int, permission: str) -> bool:
    """
    Grant a specific permission to a user.
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to grant permission to
        permission: Permission to grant (player_manage, config_manage, system)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First, get current permissions
        current = await get_user_permissions(bot, user_id)
        
        # If already has the permission, do nothing
        if permission in current:
            return True
        
        # Add the new permission
        current.append(permission)
        
        # Update database (upsert = create if doesn't exist)
        await bot.db.user_permissions.update_one(
            {"user_id": user_id},
            {"$set": {"permissions": current}},
            upsert=True
        )
        print(f"[DEBUG] add_permission: {user_id} granted {permission}")
        return True
    except Exception as e:
        print(f"[ERROR] add_permission failed for {user_id}, {permission}: {e}")
        return False


async def remove_permission(bot, user_id: int, permission: str) -> bool:
    """
    Remove a specific permission from a user.
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to remove permission from
        permission: Permission to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current permissions
        current = await get_user_permissions(bot, user_id)
        
        # If doesn't have the permission, do nothing
        if permission not in current:
            return True
        
        # Remove the permission
        current.remove(permission)
        
        # Update database
        if current:
            await bot.db.user_permissions.update_one(
                {"user_id": user_id},
                {"$set": {"permissions": current}}
            )
        else:
            # If no permissions left, delete the document
            await bot.db.user_permissions.delete_one({"user_id": user_id})
        
        print(f"[DEBUG] remove_permission: {user_id} lost {permission}")
        return True
    except Exception as e:
        print(f"[ERROR] remove_permission failed for {user_id}, {permission}: {e}")
        return False


async def get_user_permissions(bot, user_id: int) -> list:
    """
    Get all permissions for a user.
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to get permissions for
        
    Returns:
        list: List of permission strings (empty list if none)
    """
    try:
        doc = await bot.db.user_permissions.find_one({"user_id": user_id})
        if doc and "permissions" in doc:
            return doc["permissions"]
        return []
    except Exception as e:
        print(f"[ERROR] get_user_permissions failed for {user_id}: {e}")
        return []


async def set_user_permissions(bot, user_id: int, permissions: list) -> bool:
    """
    Replace all permissions for a user with a new list.
    
    Use this carefully - it overwrites ALL existing permissions.
    
    Args:
        bot: The bot instance (for database access)
        user_id: Discord user ID to set permissions for
        permissions: List of permission strings
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if permissions:
            await bot.db.user_permissions.update_one(
                {"user_id": user_id},
                {"$set": {"permissions": permissions}},
                upsert=True
            )
        else:
            # Empty list - delete the document
            await bot.db.user_permissions.delete_one({"user_id": user_id})
        
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
    
    Args:
        permission: The permission key (e.g., "player_manage")
        
    Returns:
        str: Human-readable name, or the original if not found
    """
    return PERMISSION_NAMES.get(permission, permission)


def get_permission_description(permission: str) -> str:
    """
    Get the description for a permission.
    
    Args:
        permission: The permission key (e.g., "player_manage")
        
    Returns:
        str: Description of what the permission allows
    """
    return PERMISSION_DESCRIPTIONS.get(permission, "No description available")


print("[DEBUG] backend/permissions.py: Permission system loaded successfully")