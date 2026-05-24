"""
embeds/admin_embeds.py - Embed designs for Admin cog
Contains all embed builders for admin commands:
- Divine help menu
- Settings viewer
- Admin logging embeds
"""

import discord
from backend.helpers import format_embed_color

print("[DEBUG] admin_embeds.py: Loading admin embeds...")


# ==========================================
# DIVINE HELP MENU EMBED
# ==========================================

def divine_embed(has_player: bool, has_config: bool, has_system: bool) -> discord.Embed:
    """
    Build the embed for the !divine command (admin help menu).
    
    This embed shows different command categories based on what permissions
    the user has. It's sent as a DM to the user.
    
    Args:
        has_player: Whether user has player_manage permission
        has_config: Whether user has config_manage permission  
        has_system: Whether user has system permission
        
    Returns:
        discord.Embed: Formatted divine help menu
    """
    embed = discord.Embed(
        title="⚡ The Divine Scroll",
        description="Welcome, Divine One. Here are your sacred commands.",
        color=format_embed_color("gold")  # Gold color for divine/admin content
    )

    # ========== PLAYER MANAGEMENT SECTION ==========
    if has_player:
        embed.add_field(
            name="👤 Player Management",
            value=(
                "`!reset @user` - Erase a player's entire progress\n"
                "`!setki <num> @user` - Set a player's Ki\n"
                "`!settaels <num> @user` - Set a player's Taels\n"
                "`!setmastery <num> @user` - Set Technique Mastery\n"
                "`!setcombat <num> @user` - Set Combat Mastery\n"
                "`!fixmeridians @user` - Instantly heal meridian damage\n"
                "`!refill @user` - Restore full HP and Vitality"
            ),
            inline=False
        )

    # ========== CONFIGURATION SECTION ==========
    if has_config:
        embed.add_field(
            name="⚙️ Configuration",
            value=(
                "`!toggle <feature>` - Enable/disable features (pvp, combat, actions, etc.)\n"
                "`!set_cooldown <cmd> <sec>` - Change cooldown for any command\n"
                "`!set_emoji <name> <emoji>` - Change bot emojis\n"
                "`!set_message <key> <text>` - Change bot response messages\n"
                "`!debug <on/off>` - Toggle debug mode\n"
                "`!settings` - View all current bot settings"
            ),
            inline=False
        )

    # ========== SYSTEM SECTION ==========
    if has_system:
        embed.add_field(
            name="🔧 System",
            value=(
                "`!sync` - Register slash commands with Discord\n"
                "`!pulse` - Force a recovery heartbeat\n"
                "`!promote @user` - Grant temporary god powers\n"
                "`!demote @user` - Strip god powers\n"
                "`!allow @user <perm>` - Grant admin permissions (player_manage, config_manage, system)\n"
                "`!deny @user <perm>` - Remove admin permissions\n"
                "`!perms @user` - View a user's permissions\n"
                "`!ban @user <reason>` - Ban a user from the bot\n"
                "`!unban @user` - Unban a user"
            ),
            inline=False
        )

    # ========== NO PERMISSIONS CASE ==========
    if not has_player and not has_config and not has_system:
        embed.description = "❌ You have no admin permissions."

    embed.set_footer(text="The heavens watch every step you take.")
    return embed


# ==========================================
# SETTINGS VIEWER EMBED
# ==========================================

def settings_embed(
    toggles: dict,
    cooldowns: dict,
    emojis: dict,
    messages: dict
) -> discord.Embed:
    """
    Build the embed for the !settings command.
    
    Displays all current bot configuration including feature toggles,
    command cooldowns, emoji mappings, and message templates.
    
    Args:
        toggles: Dictionary of feature_name -> enabled/disabled
                 Example: {"pvp": "True", "combat": "False"}
        cooldowns: Dictionary of command_name -> seconds
                   Example: {"work": "5", "hunt": "30"}
        emojis: Dictionary of emoji_name -> emoji string
                Example: {"ki": "✨", "tael": "💰"}
        messages: Dictionary of message_key -> message text (preview)
                  Example: {"not_registered": "You must register first..."}
        
    Returns:
        discord.Embed: Formatted settings display embed
    """
    embed = discord.Embed(
        title="⚙️ Current Bot Settings",
        color=format_embed_color("info")  # Blue color for settings
    )

    # ========== FEATURE TOGGLES SECTION ==========
    if toggles:
        toggle_text = "\n".join([
            f"• {k}: {'✅' if v == 'True' else '❌'}" 
            for k, v in toggles.items()
        ])
        embed.add_field(name="Feature Toggles", value=toggle_text, inline=False)

    # ========== COOLDOWNS SECTION ==========
    if cooldowns:
        cd_text = "\n".join([
            f"• !{k}: {v}s" 
            for k, v in cooldowns.items()
        ])
        embed.add_field(name="Cooldowns", value=cd_text, inline=False)

    # ========== EMOJIS SECTION ==========
    if emojis:
        emoji_text = "\n".join([
            f"• {k}: {v}" 
            for k, v in emojis.items()
        ])
        embed.add_field(name="Emojis", value=emoji_text, inline=False)

    # ========== MESSAGES SECTION (preview only) ==========
    if messages:
        # Truncate long messages to 50 characters for preview
        msg_text = "\n".join([
            f"• {k}: {v[:50]}..." if len(v) > 50 else f"• {k}: {v}"
            for k, v in messages.items()
        ])
        embed.add_field(name="Messages (preview)", value=msg_text, inline=False)

    return embed


# ==========================================
# ADMIN LOG EMBED
# ==========================================

def admin_log_embed(
    command_name: str,
    user: discord.User,
    channel: discord.TextChannel,
    details: str = ""
) -> discord.Embed:
    """
    Build the embed for logging admin commands to the admin log channel.
    
    This embed is sent to a configured admin log channel whenever someone
    uses an admin command. It records who, what, where, and when.
    
    Args:
        command_name: The name of the command used (e.g., "!reset", "!ban")
        user: The discord.User who ran the command
        channel: The discord channel where the command was used
        details: Optional additional details (e.g., "Target: @user, Amount: 100")
        
    Returns:
        discord.Embed: Formatted admin log embed
    """
    embed = discord.Embed(
        title="🔧 Admin Command Used",
        description=(
            f"**Command:** `{command_name}`\n"
            f"**User:** {user} ({user.id})\n"
            f"**Channel:** {channel.mention}"
        ),
        color=format_embed_color("info"),  # Blue color for logs
        timestamp=discord.utils.utcnow()   # Auto-adds current timestamp
    )
    
    # Add details field if provided
    if details:
        embed.add_field(name="Details", value=details, inline=False)

    return embed


# ==========================================
# PERMISSION CHECK FAILURE EMBEDS
# ==========================================

def permission_denied_embed(permission_required: str) -> discord.Embed:
    """
    Build the embed for permission denied errors.
    
    Args:
        permission_required: The permission that was missing (e.g., "player_manage")
        
    Returns:
        discord.Embed: Formatted permission denied embed
    """
    return discord.Embed(
        title="❌ Permission Denied",
        description=f"You need `{permission_required}` permission to use this command.",
        color=format_embed_color("error")  # Red color for errors
    )


def permanent_god_only_embed() -> discord.Embed:
    """
    Build the embed for commands that only the Permanent God can use.
    
    Returns:
        discord.Embed: Formatted permanent god only embed
    """
    return discord.Embed(
        title="❌ Divine Restriction",
        description="Only the **Permanent God** can use this command.",
        color=format_embed_color("error")
    )


# ==========================================
# COMMAND RESULT EMBEDS
# ==========================================

def success_embed(title: str, message: str, delete_after: int = None) -> discord.Embed:
    """
    Build a generic success embed for admin command results.
    
    Args:
        title: The embed title (e.g., "✅ Permission Granted")
        message: The success message
        delete_after: Optional - if provided, adds auto-delete hint in footer
        
    Returns:
        discord.Embed: Formatted success embed
    """
    embed = discord.Embed(
        title=title,
        description=message,
        color=format_embed_color("win")  # Green color for success
    )
    
    if delete_after:
        embed.set_footer(text=f"This message will disappear in {delete_after} seconds")
    
    return embed


def error_embed(title: str, message: str) -> discord.Embed:
    """
    Build a generic error embed for admin command failures.
    
    Args:
        title: The embed title (e.g., "❌ Invalid Permission")
        message: The error message
        
    Returns:
        discord.Embed: Formatted error embed
    """
    return discord.Embed(
        title=title,
        description=message,
        color=format_embed_color("error")  # Red color for errors
    )


def info_embed(title: str, message: str) -> discord.Embed:
    """
    Build a generic info embed for admin command status.
    
    Args:
        title: The embed title
        message: The info message
        
    Returns:
        discord.Embed: Formatted info embed
    """
    return discord.Embed(
        title=title,
        description=message,
        color=format_embed_color("info")  # Blue color for info
    )


# ==========================================
# PERMISSIONS VIEWER EMBED
# ==========================================

def permissions_view_embed(target_name: str, target_id: int, permissions_list: list) -> discord.Embed:
    """
    Build the embed for the !perms command.
    
    Shows a user's current admin permissions.
    
    Args:
        target_name: Name of the user being checked
        target_id: Discord ID of the user
        permissions_list: List of permission strings the user has
        
    Returns:
        discord.Embed: Formatted permissions display embed
    """
    # Special case for Permanent God
    from backend.constants import PERMANENT_GOD
    
    if target_id == PERMANENT_GOD:
        perm_list = "👑 **Permanent God** – all permissions"
    elif permissions_list:
        perm_list = "\n".join([f"• {p}" for p in permissions_list])
    else:
        perm_list = "❌ No permissions"

    embed = discord.Embed(
        title=f"Permissions for {target_name}",
        description=perm_list,
        color=format_embed_color("info")
    )
    
    return embed


# ==========================================
# SYNC RESULT EMBEDS
# ==========================================

def sync_start_embed() -> discord.Embed:
    """Build the embed shown when syncing slash commands begins."""
    return discord.Embed(
        title="📡 Syncing with the heavens...",
        description="Registering slash commands with Discord.",
        color=format_embed_color("info")
    )


def sync_success_embed(synced_count: int) -> discord.Embed:
    """
    Build the embed shown when slash command sync succeeds.
    
    Args:
        synced_count: Number of commands successfully synced
        
    Returns:
        discord.Embed: Formatted success embed
    """
    return discord.Embed(
        title="✅ Sync Complete",
        description=f"**{synced_count}** commands registered to the `/` menu.",
        color=format_embed_color("win")
    )


def sync_failure_embed(error_message: str) -> discord.Embed:
    """
    Build the embed shown when slash command sync fails.
    
    Args:
        error_message: The error message from Discord
        
    Returns:
        discord.Embed: Formatted error embed
    """
    return discord.Embed(
        title="❌ Sync Failed",
        description=f"```\n{error_message}\n```",
        color=format_embed_color("error")
    )


print("[DEBUG] admin_embeds.py: Admin embeds loaded successfully")