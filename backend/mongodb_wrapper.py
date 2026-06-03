"""
backend/mongodb_wrapper.py - MongoDB Database Wrapper
Handles all database operations for the bot.

This file contains:
- MongoDBWrapper class (connection, collections, indexes)
- All database helper methods (fetch_user, add_item, etc.)
"""

import datetime
from motor.motor_asyncio import AsyncIOMotorClient

print("[DEBUG] mongodb_wrapper.py: Loading MongoDB wrapper...")

class MongoDBWrapper:
    """
    MongoDB wrapper that provides async database methods for the bot.
    All cogs use this class to interact with the database.
    """

    def __init__(self, uri, db_name):
        """
        Initialize the MongoDB wrapper with connection details.

        Args:
            uri (str): MongoDB Atlas connection string
            db_name (str): Name of the database to use
        """
        self.client = None
        self.db = None
        self.uri = uri
        self.db_name = db_name

        # Collections (these replace SQL tables)
        self.users = None
        self.bot_settings = None
        self.admin_permissions = None
        self.user_cooldowns = None
        self.banned_users = None
        self.inventory = None
        self.admin_logs = None
        self.admins = None
        self.blocked_channels = None  # NEW: For storing blocked channels
        self.temp_gods = None  # NEW: For Temporary God status

    async def connect(self):
        """
        Establish connection to MongoDB Atlas and initialize collections.
        Creates all necessary indexes for performance.
        """
        if not self.uri:
            raise ValueError("MONGODB_URI not set")

        # Connect to MongoDB
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client[self.db_name]

        # Initialize collection references
        self.users = self.db.users
        self.bot_settings = self.db.bot_settings
        self.admin_permissions = self.db.admin_permissions
        self.user_cooldowns = self.db.user_cooldowns
        self.banned_users = self.db.banned_users
        self.inventory = self.db.inventory
        self.admin_logs = self.db.admin_logs
        self.admins = self.db.admins
        self.blocked_channels = self.db.blocked_channels  # NEW: Blocked channels collection
        self.temp_gods = self.db.temp_gods  # NEW: Temp gods collection

        # Create indexes for better query performance
        # Each index speeds up specific types of queries
        await self.users.create_index([("user_id", 1)], unique=True)
        await self.bot_settings.create_index([("setting_key", 1)], unique=True)
        await self.admin_permissions.create_index([("user_id", 1), ("permission", 1)], unique=True)
        await self.user_cooldowns.create_index([("cooldown_key", 1)], unique=True)
        await self.banned_users.create_index([("user_id", 1)], unique=True)
        await self.inventory.create_index([("user_id", 1), ("item_name", 1)], unique=True)
        await self.admin_logs.create_index([("timestamp", -1)])
        await self.admins.create_index([("user_id", 1)], unique=True)
        await self.blocked_channels.create_index([("channel_id", 1)], unique=True)  # NEW: Index for blocked_channels
        await self.temp_gods.create_index([("user_id", 1)], unique=True)  # NEW: Index for temp_gods

        print("[DEBUG] MongoDB connected and indexes created")
        return self

    async def close(self):
        """Close the MongoDB connection gracefully."""
        if self.client:
            self.client.close()

    # ==========================================
    # USER METHODS
    # ==========================================

    async def fetch_user(self, user_id):
        """
        Get a user's complete data document.

        Args:
            user_id (int): Discord user ID

        Returns:
            dict or None: User document if found, else None
        """
        return await self.users.find_one({"user_id": user_id})

    async def user_exists(self, user_id):
        """
        Check if a user exists in the database.

        Args:
            user_id (int): Discord user ID

        Returns:
            bool: True if user exists, False otherwise
        """
        return await self.users.find_one({"user_id": user_id}) is not None

    async def update_user(self, user_id, update_data):
        """
        Update a user's document with new data.

        Args:
            user_id (int): Discord user ID
            update_data (dict): Dictionary of fields to update
        """
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": update_data},
            upsert=True
        )

    async def get_user_stat(self, user_id, stat_name):
        """
        Get a single statistic from a user's document.

        Args:
            user_id (int): Discord user ID
            stat_name (str): Name of the field to retrieve

        Returns:
            Any: Value of the field, or None if user not found
        """
        user = await self.fetch_user(user_id)
        return user.get(stat_name) if user else None

    async def update_user_stat(self, user_id, stat_name, value):
        """
        Update a single statistic in a user's document.

        Args:
            user_id (int): Discord user ID
            stat_name (str): Name of the field to update
            value (Any): New value for the field
        """
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {stat_name: value}},
            upsert=True
        )

    # ==========================================
    # INVENTORY METHODS
    # ==========================================

    async def get_inventory(self, user_id):
        """
        Get all items in a user's inventory.

        Args:
            user_id (int): Discord user ID

        Returns:
            list: List of item documents with name, quantity, bound status
        """
        cursor = self.inventory.find({"user_id": user_id})
        return await cursor.to_list(length=100)

    async def add_item(self, user_id, item_name, quantity=1, bound=False):
        """
        Add an item to a user's inventory.

        Args:
            user_id (int): Discord user ID
            item_name (str): Name of the item
            quantity (int): Number of items to add (default 1)
            bound (bool): If True, item cannot be traded or sold
        """
        await self.inventory.update_one(
            {"user_id": user_id, "item_name": item_name},
            {"$inc": {"quantity": quantity}, "$set": {"bound": 1 if bound else 0}},
            upsert=True
        )

    async def remove_item(self, user_id, item_name, quantity=1):
        """
        Remove an item from a user's inventory.

        Args:
            user_id (int): Discord user ID
            item_name (str): Name of the item
            quantity (int): Number of items to remove

        Returns:
            bool: True if successful, False if not enough items
        """
        item = await self.inventory.find_one({"user_id": user_id, "item_name": item_name})
        if not item or item.get("quantity", 0) < quantity:
            return False
        if item["quantity"] == quantity:
            await self.inventory.delete_one({"user_id": user_id, "item_name": item_name})
        else:
            await self.inventory.update_one(
                {"user_id": user_id, "item_name": item_name},
                {"$inc": {"quantity": -quantity}}
            )
        return True

    async def has_item(self, user_id, item_name, quantity=1):
        """
        Check if a user has at least a certain quantity of an item.

        Args:
            user_id (int): Discord user ID
            item_name (str): Name of the item
            quantity (int): Minimum quantity required

        Returns:
            bool: True if user has enough, False otherwise
        """
        item = await self.inventory.find_one({"user_id": user_id, "item_name": item_name})
        return item is not None and item.get("quantity", 0) >= quantity

    async def update_item_name(self, user_id, old_name, new_name):
        """
        Update an item's name (used for item mutation on breakthrough).

        Args:
            user_id (int): Discord user ID
            old_name (str): Current item name
            new_name (str): New item name

        Returns:
            bool: True if successful, False otherwise
        """
        result = await self.inventory.update_one(
            {"user_id": user_id, "item_name": old_name},
            {"$set": {"item_name": new_name}}
        )
        return result.modified_count > 0

    # ==========================================
    # BOT SETTINGS METHODS
    # ==========================================

    async def get_bot_setting(self, key, default=None):
        """
        Get a bot setting from the bot_settings collection.

        Args:
            key (str): Setting key
            default (Any): Default value if setting not found

        Returns:
            Any: Setting value (converted to int/bool if applicable)
        """
        doc = await self.bot_settings.find_one({"setting_key": key})
        if not doc:
            return default
        value = doc.get("setting_value")
        if value == "True":
            return True
        if value == "False":
            return False
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value

    async def set_bot_setting(self, key, value):
        """
        Set a bot setting in the bot_settings collection.

        Args:
            key (str): Setting key
            value (Any): Value to store (converted to string)
        """
        await self.bot_settings.update_one(
            {"setting_key": key},
            {"$set": {"setting_value": str(value)}},
            upsert=True
        )

    # ==========================================
    # PERMISSION METHODS
    # ==========================================

    async def get_user_permissions(self, user_id):
        """
        Get all permission strings for a user.

        Args:
            user_id (int): Discord user ID

        Returns:
            list: List of permission strings (e.g., "player_manage")
        """
        cursor = self.admin_permissions.find({"user_id": user_id})
        docs = await cursor.to_list(length=10)
        return [doc["permission"] for doc in docs]

    async def add_user_permission(self, user_id, permission):
        """
        Grant a permission to a user.

        Args:
            user_id (int): Discord user ID
            permission (str): Permission to grant
        """
        await self.admin_permissions.update_one(
            {"user_id": user_id, "permission": permission},
            {"$set": {"user_id": user_id, "permission": permission}},
            upsert=True
        )

    async def remove_user_permission(self, user_id, permission):
        """
        Remove a permission from a user.

        Args:
            user_id (int): Discord user ID
            permission (str): Permission to remove
        """
        await self.admin_permissions.delete_one({"user_id": user_id, "permission": permission})

    # ==========================================
    # BAN METHODS
    # ==========================================

    async def is_user_banned(self, user_id):
        """
        Check if a user is banned from the bot.

        Args:
            user_id (int): Discord user ID

        Returns:
            bool: True if banned, False otherwise
        """
        return await self.banned_users.find_one({"user_id": user_id}) is not None

    async def ban_user(self, user_id, reason, banned_by):
        """
        Ban a user from using the bot.

        Args:
            user_id (int): Discord user ID
            reason (str): Reason for the ban
            banned_by (int): Discord ID of the admin who banned
        """
        await self.banned_users.update_one(
            {"user_id": user_id},
            {"$set": {
                "reason": reason,
                "banned_at": datetime.datetime.now().isoformat(),
                "banned_by": banned_by
            }},
            upsert=True
        )

    async def unban_user(self, user_id):
        """
        Unban a user.

        Args:
            user_id (int): Discord user ID
        """
        await self.banned_users.delete_one({"user_id": user_id})

    # ==========================================
    # COOLDOWN METHODS
    # ==========================================

    async def get_user_cooldown(self, cooldown_key):
        """
        Get the last used timestamp for a cooldown key.

        Args:
            cooldown_key (str): Unique key for the cooldown

        Returns:
            datetime or None: Last used timestamp, or None if not found
        """
        doc = await self.user_cooldowns.find_one({"cooldown_key": cooldown_key})
        if doc:
            try:
                return datetime.datetime.fromisoformat(doc["last_used"])
            except:
                return None
        return None

    async def set_user_cooldown(self, cooldown_key):
        """
        Set the current timestamp for a cooldown key.

        Args:
            cooldown_key (str): Unique key for the cooldown
        """
        await self.user_cooldowns.update_one(
            {"cooldown_key": cooldown_key},
            {"$set": {"last_used": datetime.datetime.now().isoformat()}},
            upsert=True
        )

    # ==========================================
    # ADMIN LOG METHODS
    # ==========================================

    async def log_admin_action(self, admin_id, action, target_id=None, details=None):
        """
        Log an admin action to the admin_logs collection.

        Args:
            admin_id (int): Discord ID of the admin
            action (str): Name of the command/action
            target_id (int, optional): Target user ID if applicable
            details (str, optional): Additional details about the action
        """
        await self.admin_logs.insert_one({
            "admin_id": admin_id,
            "action": action,
            "target_id": target_id,
            "details": details,
            "timestamp": datetime.datetime.now().isoformat()
        })

    async def get_admin_logs(self, limit=10):
        """
        Get the most recent admin actions.

        Args:
            limit (int): Maximum number of logs to return

        Returns:
            list: List of admin log documents
        """
        cursor = self.admin_logs.find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    # ==========================================
    # LEGACY ADMIN METHODS
    # ==========================================

    async def get_admins(self):
        """
        Get all admin user IDs from the admins collection.

        Returns:
            list: List of user IDs
        """
        cursor = self.admins.find({})
        admins = await cursor.to_list(length=100)
        return [admin["user_id"] for admin in admins]

    async def add_admin(self, user_id):
        """
        Add a user to the admins collection.

        Args:
            user_id (int): Discord user ID
        """
        await self.admins.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )

    async def remove_admin(self, user_id):
        """
        Remove a user from the admins collection.

        Args:
            user_id (int): Discord user ID
        """
        await self.admins.delete_one({"user_id": user_id})

    # ==========================================
    # INITIALIZATION
    # ==========================================

    async def initialize_default_settings(self):
        """
        Initialize default bot settings if they don't already exist.
        This ensures all feature toggles and costs have default values.
        """
        default_settings = [
            ("toggle_actions", "True"),
            ("actions_vit_cost_work", "10"),
            ("actions_vit_cost_observe", "10"),
            ("actions_vit_cost_comprehend", "40"),
            ("toggle_status", "True"),
            ("toggle_profile", "True"),
            ("toggle_pavilion", "True"),
            ("toggle_pvp", "True"),
            ("toggle_core", "True"),
            ("toggle_combat", "True"),
            ("toggle_mechanics", "True"),
            ("toggle_cultivation", "True"),
            ("toggle_help", "True"),
            ("toggle_shop", "True"),
            ("toggle_professions", "True"),
            # Command toggles
            ("cmd_work", "True"),
            ("cmd_observe", "True"),
            ("cmd_comprehend", "True"),
            # System settings
            ("maintenance_mode", "False"),
            ("debug_mode", "False"),
            # Cooldowns
            ("cooldown_comprehend", "1800"),
        ]
        for key, value in default_settings:
            await self.bot_settings.update_one(
                {"setting_key": key},
                {"$set": {"setting_value": value}},
                upsert=True
            )
        print("[DEBUG] Default bot_settings initialized")

print("[DEBUG] mongodb_wrapper.py: MongoDB wrapper loaded successfully")
