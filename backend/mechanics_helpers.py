"""
backend/mechanics_helpers.py - Helper functions and state management for Mechanics cog

This module handles:
- MechanicsState class (stores meditation sets, cooldown dicts)
- HeartbeatManager class (handles the 20-minute regeneration loop)
- Cooldown helpers (check, set, format)
- Meditation helpers (start, progress, cancel)
- Regeneration calculations
"""

import asyncio
import logging
import datetime
from typing import Optional, Dict, Set, Tuple
from collections import defaultdict

import discord
from discord.ext import tasks

from backend.helpers import get_max_stats
from backend.db import get_bot_setting
from backend.constants import HEARTBEAT_REGEN
from embeds.mechanics_embeds import (
    heartbeat_dm_embed,
    meditation_progress_embed
)

log = logging.getLogger(__name__)

print("[DEBUG] mechanics_helpers.py: Loading mechanics helpers...")


# ==========================================
# TIME UTILITIES
# ==========================================

def get_utc_now() -> datetime.datetime:
    """
    Get current UTC time with timezone info.
    
    Returns:
        datetime.datetime: Current UTC time
    """
    return datetime.datetime.now(datetime.timezone.utc)


def format_cooldown_time(seconds: int) -> str:
    """
    Format seconds into a human-readable string.
    
    Args:
        seconds: Number of seconds
        
    Returns:
        str: Formatted time (e.g., "5m 30s", "90s", "1 hour")
        
    Example:
        >>> format_cooldown_time(65)
        '1m 5s'
        >>> format_cooldown_time(3600)
        '1 hour'
    """
    if seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    elif seconds >= 60:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds}s"
        return f"{minutes} minutes" if minutes > 1 else f"{minutes} minute"
    else:
        return f"{seconds} seconds" if seconds != 1 else f"{seconds} second"


# ==========================================
# COOLDOWN MANAGEMENT
# ==========================================

class CooldownManager:
    """
    Manages cooldowns for commands.
    Stores cooldown end times and provides check/set functionality.
    """
    
    def __init__(self):
        """Initialize empty cooldown dictionary."""
        self._cooldowns: Dict[str, datetime.datetime] = {}
    
    def get_remaining(self, user_id: int, cooldown_type: str = "default") -> Optional[int]:
        """
        Get remaining seconds on a cooldown.
        
        Args:
            user_id: Discord user ID
            cooldown_type: Type of cooldown (e.g., "recover", "focus", "rest")
            
        Returns:
            Optional[int]: Seconds remaining, or None if no cooldown
        """
        key = f"{user_id}:{cooldown_type}"
        end_time = self._cooldowns.get(key)
        
        if not end_time:
            return None
        
        now = get_utc_now()
        if now >= end_time:
            # Cooldown expired, clean it up
            del self._cooldowns[key]
            return None
        
        return int((end_time - now).total_seconds())
    
    def set_cooldown(self, user_id: int, cooldown_type: str, duration_seconds: int):
        """
        Set a cooldown for a user.
        
        Args:
            user_id: Discord user ID
            cooldown_type: Type of cooldown (e.g., "recover", "focus", "rest")
            duration_seconds: How long the cooldown lasts
        """
        key = f"{user_id}:{cooldown_type}"
        self._cooldowns[key] = get_utc_now() + datetime.timedelta(seconds=duration_seconds)
    
    def clear_cooldown(self, user_id: int, cooldown_type: str):
        """
        Manually clear a cooldown.
        
        Args:
            user_id: Discord user ID
            cooldown_type: Type of cooldown to clear
        """
        key = f"{user_id}:{cooldown_type}"
        self._cooldowns.pop(key, None)


# ==========================================
# MEDITATION STATE MANAGEMENT
# ==========================================

class MeditationState:
    """
    Manages active meditation sessions.
    Tracks which users are meditating and when they started.
    """
    
    def __init__(self):
        """Initialize empty meditation tracking."""
        self.meditating: Set[int] = set()
        self.start_times: Dict[int, datetime.datetime] = {}
    
    def start_meditation(self, user_id: int) -> datetime.datetime:
        """
        Start a meditation session for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            datetime.datetime: The start time
        """
        now = get_utc_now()
        self.meditating.add(user_id)
        self.start_times[user_id] = now
        return now
    
    def cancel_meditation(self, user_id: int) -> Optional[datetime.datetime]:
        """
        Cancel a meditation session.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Optional[datetime.datetime]: Start time if user was meditating, else None
        """
        if user_id not in self.meditating:
            return None
        
        self.meditating.discard(user_id)
        return self.start_times.pop(user_id, None)
    
    def is_meditating(self, user_id: int) -> bool:
        """
        Check if a user is currently meditating.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: True if meditating
        """
        return user_id in self.meditating
    
    def get_elapsed(self, user_id: int) -> Optional[int]:
        """
        Get elapsed seconds for a user's meditation.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Optional[int]: Seconds elapsed, or None if not meditating
        """
        start = self.start_times.get(user_id)
        if not start:
            return None
        
        elapsed = int((get_utc_now() - start).total_seconds())
        return min(elapsed, 60)  # Cap at 60 seconds


# ==========================================
# HEARTBEAT MANAGER
# ==========================================

class HeartbeatManager:
    """
    Manages the 20-minute heartbeat regeneration loop.
    Restores HP and Vitality to all players every 20 minutes.
    """
    
    def __init__(self, bot):
        """
        Initialize the heartbeat manager.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.heartbeat_task = None
        self._dm_cooldown_counter = 0
    
    async def start(self):
        """Start the heartbeat task."""
        await self.bot.wait_until_ready()
        self.heartbeat_task = self._heartbeat_loop.start()
        log.info("Heartbeat manager started")
    
    def stop(self):
        """Stop the heartbeat task."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        log.info("Heartbeat manager stopped")
    
    async def process_user_regen(self, user_data: dict) -> Tuple[int, int, int, int]:
        """
        Process regeneration for a single user.
        
        Args:
            user_data: User document from database
            
        Returns:
            Tuple[int, int, int, int]: (hp_gain, vit_gain, new_hp, new_vit)
        """
        user_id = user_data.get("user_id")
        current_hp = user_data.get("hp", 0)
        current_vit = user_data.get("vitality", 0)
        rank = user_data.get("rank", "The Bound (Mortal)")
        
        # Get regen amount from constants
        regen = HEARTBEAT_REGEN.get(rank, 25)
        
        # Calculate caps
        max_stats = get_max_stats(rank)
        max_hp = max_stats["max_hp"]
        max_vit = max_stats["max_vit"]
        
        new_hp = min(current_hp + regen, max_hp)
        new_vit = min(current_vit + regen, max_vit)
        
        hp_gain = new_hp - current_hp
        vit_gain = new_vit - current_vit
        
        return hp_gain, vit_gain, new_hp, new_vit
    
    async def send_heartbeat_dm(self, user_id: int, hp_gain: int, vit_gain: int, new_hp: int, new_vit: int):
        """
        Send a DM to a user about heartbeat regeneration.
        
        Args:
            user_id: Discord user ID
            hp_gain: Amount of HP regained
            vit_gain: Amount of Vitality regained
            new_hp: New HP total
            new_vit: New Vitality total
        """
        user = self.bot.get_user(user_id)
        if not user:
            return
        
        # Rate limiting: sleep 1 second every 5 DMs to avoid hitting rate limits
        self._dm_cooldown_counter += 1
        if self._dm_cooldown_counter % 5 == 0:
            await asyncio.sleep(1)
        
        try:
            embed = heartbeat_dm_embed(hp_gain, vit_gain, new_hp, new_vit)
            await user.send(embed=embed)
        except discord.Forbidden:
            # User has DMs disabled - silently ignore
            pass
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                await asyncio.sleep(2)
                log.warning(f"Heartbeat DM rate limited for user {user_id}")
    
    @tasks.loop(minutes=20.0)
    async def _heartbeat_loop(self):
        """
        Main heartbeat loop. Runs every 20 minutes.
        Iterates through all users and restores their HP/Vitality.
        """
        db = self.bot.db
        
        # Fetch all users
        cursor = db.users.find({})
        users = await cursor.to_list(length=1000)
        
        log.info(f"Heartbeat: Processing {len(users)} users")
        
        for user_data in users:
            user_id = user_data.get("user_id")
            dm_enabled = user_data.get("heartbeat_dm", 1)
            
            # Calculate regen
            hp_gain, vit_gain, new_hp, new_vit = await self.process_user_regen(user_data)
            
            # Skip if no actual gain
            if hp_gain == 0 and vit_gain == 0:
                continue
            
            # Update database
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"hp": new_hp, "vitality": new_vit}}
            )
            
            # Send DM if enabled
            if dm_enabled:
                await self.send_heartbeat_dm(user_id, hp_gain, vit_gain, new_hp, new_vit)
        
        # Reset DM counter after each loop
        self._dm_cooldown_counter = 0
    
    @_heartbeat_loop.before_loop
    async def _before_heartbeat(self):
        """Wait for bot to be ready before starting heartbeat."""
        await self.bot.wait_until_ready()
    
    def get_next_heartbeat(self) -> Optional[datetime.datetime]:
        """
        Get the time of the next heartbeat.
        
        Returns:
            Optional[datetime.datetime]: Next heartbeat time, or None if not running
        """
        if self._heartbeat_loop.is_running():
            return self._heartbeat_loop.next_iteration
        return None


# ==========================================
# MECHANICS STATE (Combined state for the cog)
# ==========================================

class MechanicsState:
    """
    Combined state management for the Mechanics cog.
    Wraps CooldownManager and MeditationState for easy access.
    """
    
    def __init__(self, bot):
        """
        Initialize mechanics state.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.cooldowns = CooldownManager()
        self.meditation = MeditationState()
        self.heartbeat = HeartbeatManager(bot)
    
    async def start_heartbeat(self):
        """Start the heartbeat manager."""
        await self.heartbeat.start()
    
    def stop_heartbeat(self):
        """Stop the heartbeat manager."""
        self.heartbeat.stop()
    
    # ========== Cooldown shortcuts ==========
    
    def get_meditate_cooldown(self, user_id: int) -> Optional[int]:
        """Get remaining seconds on meditate cooldown."""
        return self.cooldowns.get_remaining(user_id, "meditate")
    
    def set_meditate_cooldown(self, user_id: int, duration_seconds: int = 300):
        """Set meditate cooldown (default 5 minutes)."""
        self.cooldowns.set_cooldown(user_id, "meditate", duration_seconds)
    
    def get_focus_cooldown(self, user_id: int) -> Optional[int]:
        """Get remaining seconds on focus cooldown."""
        return self.cooldowns.get_remaining(user_id, "focus")
    
    def set_focus_cooldown(self, user_id: int, duration_seconds: int = 300):
        """Set focus cooldown (default 5 minutes)."""
        self.cooldowns.set_cooldown(user_id, "focus", duration_seconds)
    
    def get_rest_cooldown(self, user_id: int) -> Optional[int]:
        """Get remaining seconds on rest cooldown."""
        return self.cooldowns.get_remaining(user_id, "rest")
    
    def set_rest_cooldown(self, user_id: int, duration_seconds: int = 3600):
        """Set rest cooldown (default 1 hour)."""
        self.cooldowns.set_cooldown(user_id, "rest", duration_seconds)
    
    # ========== Meditation shortcuts ==========
    
    def start_meditation(self, user_id: int):
        """Start a meditation session."""
        return self.meditation.start_meditation(user_id)
    
    def cancel_meditation(self, user_id: int):
        """Cancel a meditation session."""
        return self.meditation.cancel_meditation(user_id)
    
    def is_meditating(self, user_id: int) -> bool:
        """Check if user is meditating."""
        return self.meditation.is_meditating(user_id)
    
    def get_meditation_elapsed(self, user_id: int) -> Optional[int]:
        """Get elapsed seconds of meditation."""
        return self.meditation.get_elapsed(user_id)


# ==========================================
# HELPER: Check if feature is enabled
# ==========================================

async def is_mechanics_enabled(bot) -> bool:
    """
    Check if the mechanics feature is enabled in bot settings.
    
    Args:
        bot: The bot instance
        
    Returns:
        bool: True if enabled, False otherwise
    """
    return await get_bot_setting(bot.db, "toggle_mechanics", True)


print("[DEBUG] mechanics_helpers.py: Mechanics helpers loaded successfully")