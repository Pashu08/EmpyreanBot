"""
embeds/error_embeds.py - Embed designs for Error Handler
Contains the embed builder for sending error reports to the log channel.
"""

import discord
from discord import Embed
import datetime

print("[DEBUG] error_embeds.py: Loading error embeds...")


# ==========================================
# ERROR LOG EMBED (for admin log channel)
# ==========================================

def error_log_embed(
    error_message: str,
    command_name: str,
    user_name: str,
    user_id: int,
    channel_mention: str,
    error_type: str = "Unknown",
    severity: str = "MEDIUM"
) -> discord.Embed:
    """
    Build a beautiful, informative embed for logging errors to the admin channel.
    
    Args:
        error_message: The full error traceback or message
        command_name: Name of the command that failed
        user_name: Discord name of the user who triggered the error
        user_id: Discord ID of the user
        channel_mention: Mention string of the channel where error occurred
        error_type: Type of error (e.g., "BadArgument", "HTTPException")
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
        
    Returns:
        discord.Embed: Formatted error log embed
    """
    
    # Choose color based on severity
    severity_colors = {
        "LOW": 0x3498db,      # Blue
        "MEDIUM": 0xf39c12,   # Orange/Gold
        "HIGH": 0xe67e22,     # Dark Orange
        "CRITICAL": 0xe74c3c  # Red
    }
    color = severity_colors.get(severity, 0xe74c3c)
    
    # Severity emoji
    severity_emojis = {
        "LOW": "ℹ️",
        "MEDIUM": "⚠️",
        "HIGH": "⚡",
        "CRITICAL": "💀"
    }
    severity_emoji = severity_emojis.get(severity, "❌")
    
    embed = discord.Embed(
        title=f"{severity_emoji} Error Occurred",
        description=f"```py\n{error_message[:1900]}\n```",
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    # Command and user info
    embed.add_field(
        name="📟 Command",
        value=f"`{command_name}`" if command_name else "Unknown",
        inline=True
    )
    embed.add_field(
        name="👤 User",
        value=f"{user_name} (`{user_id}`)",
        inline=True
    )
    embed.add_field(
        name="📍 Channel",
        value=channel_mention,
        inline=True
    )
    
    # Error type and severity
    embed.add_field(
        name="🐞 Error Type",
        value=f"`{error_type}`",
        inline=True
    )
    embed.add_field(
        name=f"{severity_emoji} Severity",
        value=severity,
        inline=True
    )
    
    # Footer with timestamp
    embed.set_footer(text="The heavens record every misstep.")
    
    return embed


# ==========================================
# USER-FRIENDLY ERROR EMBEDS (for users)
# ==========================================

def user_cooldown_embed(seconds: int) -> discord.Embed:
    """
    Send to user when command is on cooldown.
    
    Args:
        seconds: Seconds remaining on cooldown
        
    Returns:
        discord.Embed: Friendly cooldown message
    """
    minutes = seconds // 60
    remaining = f"{minutes}m {seconds % 60}s" if minutes > 0 else f"{seconds}s"
    
    return discord.Embed(
        title="⏳ Steady Your Breathing",
        description=f"Your spiritual energy is still recovering. Wait **{remaining}** before using this again.",
        color=0xf39c12  # Orange
    )


def user_missing_argument_embed(param_name: str, command_example: str = None) -> discord.Embed:
    """
    Send to user when they miss a required argument.
    
    Args:
        param_name: Name of the missing parameter
        command_example: Example usage of the command
        
    Returns:
        discord.Embed: Friendly missing argument message
    """
    description = f"The technique requires focus: **{param_name}** is needed."
    if command_example:
        description += f"\n\n*Example:* `{command_example}`"
    
    return discord.Embed(
        title="📜 Incomplete Invocation",
        description=description,
        color=0x3498db  # Blue
    )


def user_bad_argument_embed(argument: str, expected_type: str = "number") -> discord.Embed:
    """
    Send to user when they provide an invalid argument type.
    
    Args:
        argument: What the user typed
        expected_type: What was expected (number, user, etc.)
        
    Returns:
        discord.Embed: Friendly bad argument message
    """
    return discord.Embed(
        title="❄️ The Heavens Reject That Value",
        description=f"`{argument}` is not a valid **{expected_type}**.\nPlease try again with a proper value.",
        color=0xe74c3c  # Red
    )


def user_generic_error_embed() -> discord.Embed:
    """
    Send to user for unexpected errors (keeps them calm).
    
    Returns:
        discord.Embed: Friendly generic error message
    """
    return discord.Embed(
        title="⚠️ A Ripple in the Heavens",
        description="Something unexpected occurred. The spirit beasts have been notified and will investigate.\n\n*Please try again in a moment.*",
        color=0xf39c12  # Orange
    )


def user_bot_missing_permissions_embed(permissions: list) -> discord.Embed:
    """
    Send to user when bot lacks required permissions.
    
    Args:
        permissions: List of missing permission names
        
    Returns:
        discord.Embed: Friendly permission error message
    """
    perm_list = ", ".join(permissions)
    return discord.Embed(
        title="🔒 The Bot's Hands Are Tied",
        description=f"I am missing the following permissions: `{perm_list}`\n\nPlease ask an administrator to grant them.",
        color=0xe74c3c  # Red
    )


def user_forbidden_embed() -> discord.Embed:
    """
    Send to user when bot can't access a channel or member.
    
    Returns:
        discord.Embed: Friendly forbidden message
    """
    return discord.Embed(
        title="🚪 A Sealed Path",
        description="I cannot access that channel or member. Check my permissions and role hierarchy.",
        color=0xe74c3c  # Red
    )


def user_database_error_embed() -> discord.Embed:
    """
    Send to user when database connection fails (rare).
    
    Returns:
        discord.Embed: Friendly database error message
    """
    return discord.Embed(
        title="📜 The Scrolls Are Unreachable",
        description="The sacred archives are momentarily inaccessible. The elders have been alerted.\n\n*Please try again shortly.*",
        color=0xe74c3c  # Red
    )


def user_private_message_only_embed() -> discord.Embed:
    """
    Send to user when a command only works in DMs.
    
    Returns:
        discord.Embed: Friendly DM-only message
    """
    return discord.Embed(
        title="📬 A Private Matter",
        description="This command can only be used in a **direct message** with me, not in a server.",
        color=0x3498db  # Blue
    )


def user_no_private_message_embed() -> discord.Embed:
    """
    Send to user when a command doesn't work in DMs.
    
    Returns:
        discord.Embed: Friendly server-only message
    """
    return discord.Embed(
        title="🏮 The Mortal Realm",
        description="This command can only be used in a **server channel**, not in direct messages.",
        color=0x3498db  # Blue
    )


print("[DEBUG] error_embeds.py: Error embeds loaded successfully")