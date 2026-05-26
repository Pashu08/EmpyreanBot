"""
commands/errors.py - Error handler cog for the bot
Handles all command errors gracefully with logging and user-friendly messages.

This file contains:
- ErrorHandler class with on_command_error listener
- Error severity classification
- Error rate tracking
- Automatic logging to file and Discord channel

All embeds are imported from embeds.error_embeds.
"""
  
import discord
from discord.ext import commands
import traceback
import datetime
from collections import defaultdict
from typing import Optional, Dict, Tuple

# Import config and logging
import config
from main import log_error_to_file

# Embed imports
from embeds.error_embeds import (
    error_log_embed,
    user_cooldown_embed,
    user_missing_argument_embed,
    user_bad_argument_embed,
    user_generic_error_embed,
    user_bot_missing_permissions_embed,
    user_forbidden_embed,
    user_database_error_embed,
    user_private_message_only_embed,
    user_no_private_message_embed
)

print("[DEBUG] commands/errors.py: Loading Error Handler commands...")


# ==========================================
# ERROR RATE TRACKING
# ==========================================

class ErrorTracker:
    """
    Track error rates per command and per error type.
    Helps identify problematic commands and potential spam.
    """
    
    def __init__(self):
        # Structure: {command_name: {error_type: [timestamps]}}
        self.error_history: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    
    def add_error(self, command_name: str, error_type: str):
        """
        Record an error occurrence.
        
        Args:
            command_name: Name of the command that errored
            error_type: Type of error (e.g., "BadArgument", "HTTPException")
        """
        now = datetime.datetime.now()
        self.error_history[command_name][error_type].append(now)
        
        # Clean up old entries (older than 1 hour)
        cutoff = now - datetime.timedelta(hours=1)
        for cmd in self.error_history:
            for err_type in list(self.error_history[cmd].keys()):
                self.error_history[cmd][err_type] = [
                    ts for ts in self.error_history[cmd][err_type]
                    if ts > cutoff
                ]
    
    def get_error_count(self, command_name: str, error_type: str, minutes: int = 5) -> int:
        """
        Get number of errors for a command in the last X minutes.
        
        Args:
            command_name: Name of the command
            error_type: Type of error
            minutes: Time window in minutes
            
        Returns:
            int: Number of errors in the time window
        """
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
        timestamps = self.error_history.get(command_name, {}).get(error_type, [])
        return len([ts for ts in timestamps if ts > cutoff])


# Global error tracker instance
error_tracker = ErrorTracker()


# ==========================================
# ERROR SEVERITY CLASSIFICATION
# ==========================================

def get_error_severity(error_type: str) -> Tuple[str, str]:
    """
    Determine the severity level of an error.
    
    Args:
        error_type: The class name of the error
        
    Returns:
        Tuple[str, str]: (severity, emoji)
    """
    severity_map = {
        # LOW - User errors, no action needed
        "CommandOnCooldown": ("LOW", "ℹ️"),
        "MissingRequiredArgument": ("LOW", "ℹ️"),
        "BadArgument": ("LOW", "ℹ️"),
        "CheckFailure": ("LOW", "ℹ️"),
        
        # MEDIUM - Need attention but bot still works
        "Forbidden": ("MEDIUM", "⚠️"),
        "HTTPException": ("MEDIUM", "⚠️"),
        "NotFound": ("MEDIUM", "⚠️"),
        
        # HIGH - Bot functionality affected
        "BotMissingPermissions": ("HIGH", "⚡"),
        "MissingPermissions": ("HIGH", "⚡"),
        
        # CRITICAL - Bot may crash or need restart
        "ConnectionFailure": ("CRITICAL", "💀"),
        "GatewayNotFound": ("CRITICAL", "💀"),
    }
    
    return severity_map.get(error_type, ("MEDIUM", "⚠️"))


# ==========================================
# ERROR HANDLER COG
# ==========================================

class ErrorHandler(commands.Cog):
    """
    Error handler cog - Catches and handles all command errors gracefully.
    
    Features:
    - Logs errors to file and Discord channel
    - Sends user-friendly messages to players
    - Tracks error rates per command
    - Classifies error severity
    """
    
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] ErrorHandler cog initialized")
    
    async def _send_to_log_channel(
        self,
        error_message: str,
        ctx: commands.Context,
        error: Exception,
        severity: str = "MEDIUM"
    ):
        """
        Send error details to the configured admin log channel.
        
        Args:
            error_message: The formatted error message
            ctx: Command context
            error: The original exception
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
        """
        # Check if log channel is configured
        if not config.ERROR_LOG_CHANNEL_ID:
            return
        
        # Get the log channel
        channel = self.bot.get_channel(config.ERROR_LOG_CHANNEL_ID)
        if not channel:
            print(f"[DEBUG] errors: Could not find channel {config.ERROR_LOG_CHANNEL_ID}")
            return
        
        # Build the beautiful embed
        embed = error_log_embed(
            error_message=error_message[:1900],  # Discord limit
            command_name=ctx.command.name if ctx.command else "Unknown",
            user_name=ctx.author.display_name,
            user_id=ctx.author.id,
            channel_mention=ctx.channel.mention,
            error_type=type(error).__name__,
            severity=severity
        )
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[DEBUG] errors: Failed to send error to log channel: {e}")
    
    # ==========================================
    # MAIN ERROR LISTENER
    # ==========================================
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """
        Global error handler for all command errors.
        
        This method:
        1. Logs the error
        2. Tracks error rates
        3. Sends user-friendly response
        4. Logs to admin channel for severe errors
        """
        command_name = ctx.command.name if ctx.command else "Unknown"
        error_type = type(error).__name__
        
        print(f"[DEBUG] errors.on_command_error: Command {command_name} raised {error_type}")
        
        # Track error for rate monitoring
        error_tracker.add_error(command_name, error_type)
        
        # Get severity level
        severity, severity_emoji = get_error_severity(error_type)
        
        # ========== SILENT IGNORE ==========
        # Command not found - silently ignore
        if isinstance(error, commands.CommandNotFound):
            return
        
        # ========== COOLDOWN ERROR ==========
        if isinstance(error, commands.CommandOnCooldown):
            embed = user_cooldown_embed(round(error.retry_after))
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # ========== MISSING ARGUMENT ==========
        if isinstance(error, commands.MissingRequiredArgument):
            embed = user_missing_argument_embed(
                param_name=error.param.name,
                command_example=f"!{command_name} <{error.param.name}>"
            )
            await ctx.send(embed=embed, ephemeral=True)
            # Log to channel as LOW severity
            await self._send_to_log_channel(
                f"Missing argument: {error.param.name}",
                ctx, error, "LOW"
            )
            return
        
        # ========== BAD ARGUMENT ==========
        if isinstance(error, commands.BadArgument):
            embed = user_bad_argument_embed(str(error), "valid value")
            await ctx.send(embed=embed, ephemeral=True)
            await self._send_to_log_channel(str(error), ctx, error, "LOW")
            return
        
        # ========== BOT MISSING PERMISSIONS ==========
        if isinstance(error, commands.BotMissingPermissions):
            embed = user_bot_missing_permissions_embed(error.missing_permissions)
            await ctx.send(embed=embed, ephemeral=True)
            await self._send_to_log_channel(
                f"Missing permissions: {', '.join(error.missing_permissions)}",
                ctx, error, "HIGH"
            )
            return
        
        # ========== FORBIDDEN / MISSING ACCESS ==========
        if isinstance(error, commands.Forbidden):
            embed = user_forbidden_embed()
            await ctx.send(embed=embed, ephemeral=True)
            await self._send_to_log_channel("Forbidden access", ctx, error, "MEDIUM")
            return
        
        # ========== PRIVATE MESSAGE ONLY ==========
        if isinstance(error, commands.PrivateMessageOnly):
            embed = user_private_message_only_embed()
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # ========== NO PRIVATE MESSAGE ==========
        if isinstance(error, commands.NoPrivateMessage):
            embed = user_no_private_message_embed()
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # ========== CHECK FAILURE ==========
        # Checks usually send their own messages, so we don't send another
        if isinstance(error, commands.CheckFailure):
            return
        
        # ========== DATABASE / CONNECTION ERRORS ==========
        if isinstance(error, ConnectionError) or "database" in str(error).lower():
            embed = user_database_error_embed()
            await ctx.send(embed=embed, ephemeral=True)
            await self._send_to_log_channel(str(error), ctx, error, "HIGH")
            log_error_to_file(f"DATABASE ERROR in {command_name}: {error}\n{traceback.format_exc()}")
            return
        
        # ========== HTTP EXCEPTION (Discord API) ==========
        if isinstance(error, discord.HTTPException):
            # Rate limit - don't spam log channel
            if error.status == 429:
                print(f"[WARN] Rate limited in {command_name}")
                return
            
            embed = user_generic_error_embed()
            await ctx.send(embed=embed, ephemeral=True)
            await self._send_to_log_channel(str(error), ctx, error, "MEDIUM")
            log_error_to_file(f"HTTP ERROR in {command_name}: {error}\n{traceback.format_exc()}")
            return
        
        # ========== UNHANDLED ERROR (Catch-all) ==========
        # Log everything and send generic message
        
        error_details = f"{error_type}: {error}\n{traceback.format_exc()}"
        
        # Log to file
        log_error_to_file(f"UNHANDLED ERROR in {command_name}: {error_details}")
        
        # Print to console for debugging
        print(f"[ERROR] Unhandled error in command {command_name}: {error}")
        traceback.print_exc()
        
        # Send to Discord log channel (if severe enough)
        await self._send_to_log_channel(error_details[:2000], ctx, error, "HIGH")
        
        # Send generic error message to user
        embed = user_generic_error_embed()
        await ctx.send(embed=embed, ephemeral=True)
        
        # Check for error spam - if same command errors 5+ times in 5 minutes
        error_count = error_tracker.get_error_count(command_name, error_type, minutes=5)
        if error_count >= 5:
            print(f"[WARN] Command '{command_name}' has errored {error_count} times in 5 minutes!")
            await self._send_to_log_channel(
                f"⚠️ **HIGH ERROR RATE ALERT**\n"
                f"Command `{command_name}` has failed {error_count} times in the last 5 minutes.\n"
                f"Error type: {error_type}\n"
                f"Consider disabling temporarily with `!toggle {command_name}`",
                ctx, error, "HIGH"
            )


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(ErrorHandler(bot))
    print("[DEBUG] commands/errors.py: Setup complete")