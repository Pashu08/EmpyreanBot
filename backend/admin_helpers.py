"""
backend/admin_helpers.py - Admin helper functions for logging and utilities
"""

import discord
from embeds.admin_embeds import admin_log_embed
import config

print("[DEBUG] backend/admin_helpers.py: Loading admin helpers...")

async def log_admin_command(bot, ctx, command_name: str, details: str = ""):
    """Log an admin command to the configured admin log channel."""
    # ... full function

async def can_use_admin_command(bot, user_id: int, permission: str = None) -> bool:
    """Check if a user can use an admin command."""
    # ... full function

print("[DEBUG] backend/admin_helpers.py: Admin helpers loaded successfully")