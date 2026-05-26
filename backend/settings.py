"""
backend/settings.py - Bot settings management for admin system

This module handles:
- Getting/setting bot configuration values
- Feature toggles (pvp, combat, actions, etc.)
- Cooldown management for commands
- Emoji customization
- Message templates
- Debug mode

All settings are stored in the 'bot_settings' MongoDB collection.
Each setting is a key-value pair with optional metadata.
"""

import datetime
from typing import Any, Optional

print("[DEBUG] backend/settings.py: Loading settings system...")


# ==========================================
# CORE SETTING FUNCTIONS
# ==========================================

async def get_setting(bot, key: str, default: Any = None) -> Any:
    """
    Get a setting value from the database.
    
    Args:
        bot: The bot instance (for database access)
        key: The setting key (e.g., "toggle_pvp", "cooldown_work", "emoji_ki")
        default: Default value to return if setting doesn't exist
        
    Returns:
        Any: The setting value, or default if not found
    """
    try:
        doc = await bot.db.bot_settings.find_one({"setting_key": key})
        if doc and "setting_value" in doc:
            return doc["setting_value"]
        return default
    except Exception as e:
        print(f"[ERROR] get_setting failed for key '{key}': {e}")
        return default


async def set_setting(bot, key: str, value: Any, description: str = "") -> bool:
    """
    Set a setting value in the database.
    
    Args:
        bot: The bot instance (for database access)
        key: The setting key (e.g., "toggle_pvp", "cooldown_work")
        value: The value to store (can be string, int, bool, etc.)
        description: Optional description of what this setting does
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        await bot.db.bot_settings.update_one(
            {"setting_key": key},
            {
                "$set": {
                    "setting_value": value,
                    "description": description,
                    "updated_at": datetime.datetime.now().isoformat()
                }
            },
            upsert=True
        )
        print(f"[DEBUG] set_setting: {key} = {value}")
        return True
    except Exception as e:
        print(f"[ERROR] set_setting failed for key '{key}': {e}")
        return False


async def delete_setting(bot, key: str) -> bool:
    """
    Delete a setting from the database.
    
    Args:
        bot: The bot instance (for database access)
        key: The setting key to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = await bot.db.bot_settings.delete_one({"setting_key": key})
        if result.deleted_count > 0:
            print(f"[DEBUG] delete_setting: {key} removed")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] delete_setting failed for key '{key}': {e}")
        return False


async def get_all_settings(bot, prefix: str = None) -> dict:
    """
    Get all settings, optionally filtered by key prefix.
    
    Args:
        bot: The bot instance (for database access)
        prefix: Optional key prefix to filter by (e.g., "toggle_" for all toggles)
        
    Returns:
        dict: Dictionary of setting_key -> setting_value
    """
    try:
        query = {}
        if prefix:
            query["setting_key"] = {"$regex": f"^{prefix}"}
        
        cursor = bot.db.bot_settings.find(query)
        result = {}
        async for doc in cursor:
            result[doc["setting_key"]] = doc["setting_value"]
        return result
    except Exception as e:
        print(f"[ERROR] get_all_settings failed: {e}")
        return {}


# ==========================================
# FEATURE TOGGLE FUNCTIONS
# ==========================================

# Valid feature names for toggles
VALID_FEATURES = [
    "pvp",          # Player vs Player combat
    "professions",  # Profession system (mining, herbalism, etc.)
    "bazaar",       # Player marketplace/trading
    "afk_gains",    # Offline/background progression
    "combat",       # PvE combat/hunting
    "cultivation",  # Cultivation/breakthrough system
    "items",        # Item system (inventory, usage)
    "pavilion",     # Pavilion/guild system
    "actions"       # Work/observe/comprehend actions
]


async def is_feature_enabled(bot, feature: str) -> bool:
    """
    Check if a specific feature is enabled.
    
    Args:
        bot: The bot instance (for database access)
        feature: Feature name (must be in VALID_FEATURES)
        
    Returns:
        bool: True if enabled, False if disabled or not found
    """
    key = f"toggle_{feature.lower()}"
    return await get_setting(bot, key, True)  # Default to True (enabled)


async def set_feature_enabled(bot, feature: str, enabled: bool) -> bool:
    """
    Enable or disable a feature.
    
    Args:
        bot: The bot instance (for database access)
        feature: Feature name (must be in VALID_FEATURES)
        enabled: True to enable, False to disable
        
    Returns:
        bool: True if successful, False otherwise
    """
    if feature.lower() not in VALID_FEATURES:
        print(f"[WARN] set_feature_enabled: Invalid feature '{feature}'")
        return False
    
    key = f"toggle_{feature.lower()}"
    description = f"Toggle for the {feature} system. True = enabled, False = disabled."
    return await set_setting(bot, key, enabled, description)


async def get_all_toggles(bot) -> dict:
    """
    Get all feature toggle settings.
    
    Args:
        bot: The bot instance (for database access)
        
    Returns:
        dict: Dictionary of feature_name -> enabled_status
    """
    settings = await get_all_settings(bot, "toggle_")
    result = {}
    for key, value in settings.items():
        # Extract feature name from "toggle_pvp" -> "pvp"
        feature_name = key[7:]  # Remove "toggle_" prefix
        result[feature_name] = value
    return result


# ==========================================
# COOLDOWN MANAGEMENT
# ==========================================

# Valid command names that can have custom cooldowns
VALID_COOLDOWN_COMMANDS = [
    "work",         # Labor action
    "observe",      # Ki refinement action
    "hunt",         # Combat/hunting action
    "recover",      # HP/Vitality recovery
    "focus",        # Ki focus/meditation
    "rest",         # Rest action
    "breakthrough", # Cultivation breakthrough
    "spar"          # PvP sparring
]


async def get_cooldown(bot, command: str, default: int = 5) -> int:
    """
    Get the cooldown (in seconds) for a specific command.
    
    Args:
        bot: The bot instance (for database access)
        command: Command name (must be in VALID_COOLDOWN_COMMANDS)
        default: Default cooldown if not set (default: 5 seconds)
        
    Returns:
        int: Cooldown in seconds
    """
    key = f"cooldown_{command.lower()}"
    return await get_setting(bot, key, default)


async def set_cooldown(bot, command: str, seconds: int) -> bool:
    """
    Set the cooldown for a specific command.
    
    Args:
        bot: The bot instance (for database access)
        command: Command name (must be in VALID_COOLDOWN_COMMANDS)
        seconds: Cooldown in seconds (must be >= 0)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if command.lower() not in VALID_COOLDOWN_COMMANDS:
        print(f"[WARN] set_cooldown: Invalid command '{command}'")
        return False
    
    if seconds < 0:
        print(f"[WARN] set_cooldown: Negative cooldown '{seconds}' for '{command}'")
        return False
    
    key = f"cooldown_{command.lower()}"
    description = f"Cooldown for the !{command} command in seconds."
    return await set_setting(bot, key, seconds, description)


async def get_all_cooldowns(bot) -> dict:
    """
    Get all command cooldown settings.
    
    Args:
        bot: The bot instance (for database access)
        
    Returns:
        dict: Dictionary of command_name -> cooldown_seconds
    """
    settings = await get_all_settings(bot, "cooldown_")
    result = {}
    for key, value in settings.items():
        # Extract command name from "cooldown_work" -> "work"
        command_name = key[9:]  # Remove "cooldown_" prefix
        result[command_name] = value
    return result


# ==========================================
# EMOJI MANAGEMENT
# ==========================================

# Valid emoji names that can be customized
VALID_EMOJI_NAMES = [
    "ki",           # Ki stat emoji
    "tael",         # Currency emoji
    "hp",           # Health Points emoji
    "vitality",     # Vitality stat emoji
    "mastery",      # Technique Mastery emoji
    "combat",       # Combat Mastery emoji
    "meditate",     # Meditation action emoji
    "work",         # Work action emoji
    "observe",      # Observe action emoji
    "breakthrough", # Breakthrough action emoji
    "success",      # Success result emoji
    "failure",      # Failure result emoji
    "cooldown"      # Cooldown indicator emoji
]

# Default emojis (fallbacks if not set in database)
DEFAULT_EMOJIS = {
    "ki": "✨",
    "tael": "💰",
    "hp": "❤️",
    "vitality": "💪",
    "mastery": "📖",
    "combat": "⚔️",
    "meditate": "🧘",
    "work": "⚒️",
    "observe": "👁️",
    "breakthrough": "🌀",
    "success": "✅",
    "failure": "❌",
    "cooldown": "⏳"
}


async def get_emoji(bot, name: str) -> str:
    """
    Get the emoji for a specific stat or action.
    
    Args:
        bot: The bot instance (for database access)
        name: Emoji name (must be in VALID_EMOJI_NAMES)
        
    Returns:
        str: The emoji string, or default if not set
    """
    if name.lower() not in VALID_EMOJI_NAMES:
        return DEFAULT_EMOJIS.get(name.lower(), "❓")
    
    key = f"emoji_{name.lower()}"
    value = await get_setting(bot, key)
    
    # Return database value if exists, otherwise default
    if value:
        return value
    return DEFAULT_EMOJIS.get(name.lower(), "❓")


async def set_emoji(bot, name: str, emoji: str) -> bool:
    """
    Set a custom emoji for a stat or action.
    
    Args:
        bot: The bot instance (for database access)
        name: Emoji name (must be in VALID_EMOJI_NAMES)
        emoji: The emoji string (e.g., "✨", "<:custom:123456789>")
        
    Returns:
        bool: True if successful, False otherwise
    """
    if name.lower() not in VALID_EMOJI_NAMES:
        print(f"[WARN] set_emoji: Invalid emoji name '{name}'")
        return False
    
    key = f"emoji_{name.lower()}"
    description = f"Emoji used for {name} in embeds and messages."
    return await set_setting(bot, key, emoji, description)


async def get_all_emojis(bot) -> dict:
    """
    Get all custom emoji settings.
    
    Args:
        bot: The bot instance (for database access)
        
    Returns:
        dict: Dictionary of emoji_name -> emoji_string
    """
    settings = await get_all_settings(bot, "emoji_")
    result = {}
    for key, value in settings.items():
        # Extract name from "emoji_ki" -> "ki"
        name = key[6:]  # Remove "emoji_" prefix
        result[name] = value
    
    # Fill in any missing emojis with defaults
    for name in VALID_EMOJI_NAMES:
        if name not in result:
            result[name] = DEFAULT_EMOJIS.get(name, "❓")
    
    return result


# ==========================================
# MESSAGE TEMPLATE MANAGEMENT
# ==========================================

# Valid message keys that can be customized
VALID_MESSAGE_KEYS = [
    "not_registered",      # User not registered in database
    "meridian_damage",     # User has meridian damage
    "cooldown",            # Command on cooldown
    "no_ki",              # Insufficient Ki
    "no_vitality",        # Insufficient Vitality
    "already_meditating", # Already in meditation
    "not_meditating",     # Not currently meditating
    "cancelled",          # Action was cancelled
    "recover_complete",   # Recovery action completed
    "focus_complete",     # Focus action completed
    "rest_complete"       # Rest action completed
]

# Default message templates (fallbacks)
DEFAULT_MESSAGES = {
    "not_registered": "❌ You are not registered. Use `!start` to begin your journey.",
    "meridian_damage": "💢 Your meridians are damaged! You cannot perform this action.",
    "cooldown": "⏳ You need to wait **{seconds}** seconds before using this again.",
    "no_ki": "✨ You don't have enough Ki. Minimum required: **{required}**",
    "no_vitality": "❤️ You don't have enough Vitality. Minimum required: **{required}**",
    "already_meditating": "🧘 You are already meditating. Use `!stop` to cancel.",
    "not_meditating": "❌ You are not currently meditating.",
    "cancelled": "🛑 Action cancelled.",
    "recover_complete": "💪 You have fully recovered your HP and Vitality!",
    "focus_complete": "🧠 Your focus has deepened. +{gain} Ki!",
    "rest_complete": "😴 You feel refreshed after resting."
}


async def get_message(bot, key: str) -> str:
    """
    Get a customized message template.
    
    Args:
        bot: The bot instance (for database access)
        key: Message key (must be in VALID_MESSAGE_KEYS)
        
    Returns:
        str: The message template, or default if not set
    """
    if key.lower() not in VALID_MESSAGE_KEYS:
        return DEFAULT_MESSAGES.get(key.lower(), "❓ Unknown message key")
    
    db_key = f"msg_{key.lower()}"
    value = await get_setting(bot, db_key)
    
    if value:
        return value
    return DEFAULT_MESSAGES.get(key.lower(), "❓ Message not found")


async def set_message(bot, key: str, template: str) -> bool:
    """
    Set a custom message template.
    
    Use {variable} placeholders for dynamic content.
    Example: "You gained {amount} Ki!"
    
    Args:
        bot: The bot instance (for database access)
        key: Message key (must be in VALID_MESSAGE_KEYS)
        template: The message template string
        
    Returns:
        bool: True if successful, False otherwise
    """
    if key.lower() not in VALID_MESSAGE_KEYS:
        print(f"[WARN] set_message: Invalid message key '{key}'")
        return False
    
    db_key = f"msg_{key.lower()}"
    description = f"Custom message template for {key}."
    return await set_setting(bot, db_key, template, description)


async def get_all_messages(bot) -> dict:
    """
    Get all custom message templates.
    
    Args:
        bot: The bot instance (for database access)
        
    Returns:
        dict: Dictionary of message_key -> template_string
    """
    settings = await get_all_settings(bot, "msg_")
    result = {}
    for key, value in settings.items():
        # Extract key from "msg_not_registered" -> "not_registered"
        name = key[4:]  # Remove "msg_" prefix
        result[name] = value
    
    # Fill in any missing messages with defaults
    for key in VALID_MESSAGE_KEYS:
        if key not in result:
            result[key] = DEFAULT_MESSAGES.get(key, "❓ Message not found")
    
    return result


# ==========================================
# DEBUG MODE
# ==========================================

async def is_debug_mode(bot) -> bool:
    """
    Check if debug mode is enabled.
    
    Debug mode enables additional logging and verbose error messages.
    
    Args:
        bot: The bot instance (for database access)
        
    Returns:
        bool: True if debug mode is enabled, False otherwise
    """
    return await get_setting(bot, "debug_mode", False)


async def set_debug_mode(bot, enabled: bool) -> bool:
    """
    Enable or disable debug mode.
    
    Args:
        bot: The bot instance (for database access)
        enabled: True to enable, False to disable
        
    Returns:
        bool: True if successful, False otherwise
    """
    description = "Debug mode enables additional logging and verbose errors."
    return await set_setting(bot, "debug_mode", enabled, description)


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

async def reset_all_settings(bot) -> dict:
    """
    Reset ALL bot settings to their defaults.
    
    WARNING: This will delete all custom settings!
    
    Args:
        bot: The bot instance (for database access)
        
    Returns:
        dict: Summary of what was reset
    """
    summary = {
        "toggles_reset": 0,
        "cooldowns_reset": 0,
        "emojis_reset": 0,
        "messages_reset": 0
    }
    
    # Delete all settings
    await bot.db.bot_settings.delete_many({})
    
    # Re-initialize with defaults (optional)
    # This would call a function to set up default settings
    
    print("[WARN] reset_all_settings: All bot settings have been deleted!")
    return summary


async def get_setting_with_metadata(bot, key: str) -> dict:
    """
    Get a setting along with its metadata (description, updated_at).
    
    Args:
        bot: The bot instance (for database access)
        key: The setting key
        
    Returns:
        dict: Setting document with metadata, or None if not found
    """
    try:
        doc = await bot.db.bot_settings.find_one({"setting_key": key})
        if doc:
            return {
                "key": doc["setting_key"],
                "value": doc["setting_value"],
                "description": doc.get("description", ""),
                "updated_at": doc.get("updated_at", "Unknown")
            }
        return None
    except Exception as e:
        print(f"[ERROR] get_setting_with_metadata failed for '{key}': {e}")
        return None


print("[DEBUG] backend/settings.py: Settings system loaded successfully")