"""
commands/admin.py - Command logic for Admin cog
Contains all admin command implementations.
Embed designs are imported from embeds.admin_embeds.
Permission helpers are imported from backend.permissions.
Settings helpers are imported from backend.settings.
"""

import discord
from discord.ext import commands
import datetime
import asyncio

# Backend imports
from backend.permissions import (
    has_permission,
    add_permission,
    remove_permission,
    get_user_permissions,
    is_temp_god,
    add_temp_god,
    remove_temp_god
)
from backend.settings import get_setting, set_setting
from backend.constants import PERMANENT_GOD
from backend.admin_helpers import log_admin_command, format_inventory_for_admin

# Embed imports
from embeds.admin_embeds import (
    divine_embed,
    settings_embed,
    admin_log_embed,
    permission_denied_embed,
    permanent_god_only_embed,
    success_embed,
    error_embed,
    info_embed,
    permissions_view_embed,
    sync_start_embed,
    sync_success_embed,
    sync_failure_embed,
    inventory_inspect_embed,
    item_removed_embed
)

import config

print("[DEBUG] commands/admin.py: Loading Admin commands...")

class Admin(commands.Cog):
    """
    Admin cog - Contains all administrator commands.

    Permission Levels:
    - Permanent God: Full access to everything (hardcoded user ID)
    - Temporary God: Full access (stored in database, granted via !promote)
    - player_manage: Can modify player stats (reset, setki, settaels, etc.)
    - config_manage: Can change bot settings (toggle, set_cooldown, etc.)
    - system: Can use system commands (sync, promote, ban, etc.)
    """

    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Admin cog initialized")

    # ==========================================
    # PERMISSION MANAGEMENT COMMANDS
    # ==========================================

    @commands.command(name="allow")
    async def allow(self, ctx, member: discord.Member, permission: str):
        """
        Grant a permission to a user.

        Usage: !allow @user <permission>
        Permissions: player_manage, config_manage, system, all

        Note: Only the Permanent God can use this command.
        """
        # Permission check - only Permanent God
        if ctx.author.id != PERMANENT_GOD:
            embed = permanent_god_only_embed()
            await ctx.send(embed=embed, delete_after=2)
            return

        # Delete the command message for cleanliness
        await ctx.message.delete()

        # Log the command usage
        await log_admin_command(self.bot, ctx, "!allow", f"Target: {member.id}, Permission: {permission}")

        # Validate permission name
        valid_perms = ["player_manage", "config_manage", "system", "all"]
        if permission.lower() not in valid_perms:
            embed = error_embed(
                "❌ Invalid Permission",
                f"Choose from: {', '.join(valid_perms)}"
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        # Grant permission(s)
        if permission.lower() == "all":
            for perm in ["player_manage", "config_manage", "system"]:
                await add_permission(self.bot, member.id, perm)
            embed = success_embed(
                "✅ All Permissions Granted",
                f"{member.mention} granted **ALL** permissions."
            )
            await ctx.send(embed=embed, delete_after=2)
        else:
            await add_permission(self.bot, member.id, permission.lower())
            embed = success_embed(
                "✅ Permission Granted",
                f"{member.mention} granted `{permission}` permission."
            )
            await ctx.send(embed=embed, delete_after=2)

        print(f"[DEBUG] !allow {member.id} {permission} by {ctx.author.id}")

    @commands.command(name="deny")
    async def deny(self, ctx, member: discord.Member, permission: str):
        """
        Remove a permission from a user.

        Usage: !deny @user <permission>
        Permissions: player_manage, config_manage, system, all

        Note: Only the Permanent God can use this command.
        """
        # Permission check - only Permanent God
        if ctx.author.id != PERMANENT_GOD:
            embed = permanent_god_only_embed()
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!deny", f"Target: {member.id}, Permission: {permission}")

        # Validate permission name
        valid_perms = ["player_manage", "config_manage", "system", "all"]
        if permission.lower() not in valid_perms:
            embed = error_embed(
                "❌ Invalid Permission",
                f"Choose from: {', '.join(valid_perms)}"
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        # Remove permission(s)
        if permission.lower() == "all":
            for perm in ["player_manage", "config_manage", "system"]:
                await remove_permission(self.bot, member.id, perm)
            embed = success_embed(
                "✅ All Permissions Removed",
                f"Removed **ALL** permissions from {member.mention}."
            )
            await ctx.send(embed=embed, delete_after=2)
        else:
            await remove_permission(self.bot, member.id, permission.lower())
            embed = success_embed(
                "✅ Permission Removed",
                f"Removed `{permission}` permission from {member.mention}."
            )
            await ctx.send(embed=embed, delete_after=2)

        print(f"[DEBUG] !deny {member.id} {permission} by {ctx.author.id}")

    @commands.command(name="perms")
    async def perms(self, ctx, member: discord.Member = None):
        """
        View a user's admin permissions.

        Usage: !perms [@user]
        If no user is specified, shows your own permissions.
        """
        # Permission check - need system permission (or be Permanent/Temp God)
        if not await has_permission(self.bot, ctx.author.id, "system"):
            if ctx.author.id != PERMANENT_GOD and not await is_temp_god(self.bot, ctx.author.id):
                embed = permission_denied_embed("system")
                await ctx.send(embed=embed, delete_after=2)
                return

        await ctx.message.delete()

        target = member or ctx.author
        perms = await get_user_permissions(self.bot, target.id)

        embed = permissions_view_embed(target.name, target.id, perms)
        await ctx.send(embed=embed, delete_after=15)

    # ==========================================
    # SLASH COMMAND SYNC
    # ==========================================

    @commands.command(name="sync")
    async def sync(self, ctx):
        """
        Sync slash commands with Discord.

        Usage: !sync
        This registers all / commands with Discord (can take a few seconds).
        """
        # Permission check
        if not await has_permission(self.bot, ctx.author.id, "system"):
            embed = permission_denied_embed("system")
            await ctx.send(embed=embed, delete_after=2)
            return

        await log_admin_command(self.bot, ctx, "!sync")
        print(f"[DEBUG] !sync used by {ctx.author.id}")

        # Send start message
        embed = sync_start_embed()
        await ctx.send(embed=embed)

        try:
            synced = await self.bot.tree.sync()
            embed = sync_success_embed(len(synced))
            await ctx.send(embed=embed)
        except Exception as e:
            embed = sync_failure_embed(str(e))
            await ctx.send(embed=embed)

    # ==========================================
    # DIVINE HELP MENU
    # ==========================================

    @commands.command(name="divine")
    async def divine(self, ctx):
        """
        Show the admin help menu (sent via DM).

        Usage: !divine
        Shows different commands based on your permissions.
        """
        await ctx.message.delete()
        print(f"[DEBUG] !divine used by {ctx.author.id}")

        # Check user's permissions
        has_player = await has_permission(self.bot, ctx.author.id, "player_manage")
        has_config = await has_permission(self.bot, ctx.author.id, "config_manage")
        has_system = await has_permission(self.bot, ctx.author.id, "system")

        # Also check if user is Permanent God or Temporary God
        is_god = (ctx.author.id == PERMANENT_GOD) or await is_temp_god(self.bot, ctx.author.id)

        if is_god:
            has_player = has_config = has_system = True

        embed = divine_embed(has_player, has_config, has_system)

        try:
            await ctx.author.send(embed=embed)
            # If DM successful, send a confirmation in channel that disappears
            await ctx.send("📬 Divine scroll sent to your DMs!", delete_after=2)
        except discord.Forbidden:
            # User has DMs disabled
            embed = error_embed(
                "❌ Cannot Send DM",
                "Please enable DMs to receive the divine scroll."
            )
            await ctx.send(embed=embed, delete_after=5)

    # ==========================================
    # DIVINE PULSE (Heartbeat trigger)
    # ==========================================

    @commands.command(name="pulse")
    async def pulse(self, ctx):
        """
        Force a recovery heartbeat.

        Usage: !pulse
        Triggers the mechanics heartbeat to restore player stats.
        """
        if not await has_permission(self.bot, ctx.author.id, "system"):
            embed = permission_denied_embed("system")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!pulse")
        print(f"[DEBUG] !pulse used by {ctx.author.id}")

        mechanics_cog = self.bot.get_cog('Mechanics')
        if mechanics_cog:
            await mechanics_cog.heartbeat()
            embed = info_embed("🌀 Divine Pulse", "Recovery heartbeat triggered.")
            await ctx.send(embed=embed, delete_after=2)
        else:
            embed = error_embed("❌ Error", "Mechanics cog not found.")
            await ctx.send(embed=embed, delete_after=2)

    # ==========================================
    # TEMPORARY GOD MANAGEMENT
    # ==========================================

    @commands.command(name="promote")
    async def promote(self, ctx, member: discord.Member):
        """
        Promote a user to Temporary God.

        Usage: !promote @user
        Temporary Gods have all permissions (like Permanent God).

        Note: Only the Permanent God can use this command.
        """
        if ctx.author.id != PERMANENT_GOD:
            embed = permanent_god_only_embed()
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!promote", f"Target: {member.id}")

        await add_temp_god(self.bot, member.id)
        print(f"[DEBUG] !promote {member.id} by {ctx.author.id}")

        embed = success_embed(
            "🌟 Promoted to Temporary God",
            f"{member.mention} now has divine powers."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="demote")
    async def demote(self, ctx, member: discord.Member):
        """
        Remove Temporary God status from a user.

        Usage: !demote @user

        Note: Only the Permanent God can use this command.
        """
        if ctx.author.id != PERMANENT_GOD:
            embed = permanent_god_only_embed()
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!demote", f"Target: {member.id}")

        if await is_temp_god(self.bot, member.id):
            await remove_temp_god(self.bot, member.id)
            print(f"[DEBUG] !demote {member.id} by {ctx.author.id}")
            embed = success_embed(
                "💢 Divine Power Stripped",
                f"{member.mention} has been demoted from godhood."
            )
            await ctx.send(embed=embed, delete_after=2)
        else:
            embed = error_embed(
                "❌ Not a God",
                f"{member.mention} is not a Temporary God."
            )
            await ctx.send(embed=embed, delete_after=2)

    # ==========================================
    # PLAYER MANAGEMENT COMMANDS
    # Requires player_manage permission
    # ==========================================

    @commands.command(name="reset")
    async def reset(self, ctx, member: discord.Member = None):
        """Erase a player's entire progress."""
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        target = member or ctx.author
        await log_admin_command(self.bot, ctx, "!reset", f"Target: {target.id}")
        print(f"[DEBUG] !reset {target.id} by {ctx.author.id}")

        await self.bot.db.users.delete_one({"user_id": target.id})
        embed = success_embed(
            "♻️ Divine Reset",
            f"{target.name} erased from history."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="setki")
    async def setki(self, ctx, amount: int, member: discord.Member = None):
        """Set a player's Ki."""
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        target = member or ctx.author
        await log_admin_command(self.bot, ctx, "!setki", f"Target: {target.id}, Amount: {amount}")
        print(f"[DEBUG] !setki {amount} for {target.id} by {ctx.author.id}")

        await self.bot.db.users.update_one(
            {"user_id": target.id},
            {"$set": {"ki": amount}},
            upsert=True
        )
        embed = success_embed(
            "✨ Ki Set",
            f"Ki set to {amount} for {target.name}."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="settaels")
    async def settaels(self, ctx, amount: int, member: discord.Member = None):
        """Set a player's Taels."""
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        target = member or ctx.author
        await log_admin_command(self.bot, ctx, "!settaels", f"Target: {target.id}, Amount: {amount}")
        print(f"[DEBUG] !settaels {amount} for {target.id} by {ctx.author.id}")

        await self.bot.db.users.update_one(
            {"user_id": target.id},
            {"$set": {"taels": amount}},
            upsert=True
        )
        embed = success_embed(
            "💰 Taels Set",
            f"Taels set to {amount} for {target.name}."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="setmastery")
    async def setmastery(self, ctx, amount: float, member: discord.Member = None):
        """Set a player's Technique Mastery."""
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        target = member or ctx.author
        await log_admin_command(self.bot, ctx, "!setmastery", f"Target: {target.id}, Amount: {amount}")
        print(f"[DEBUG] !setmastery {amount} for {target.id} by {ctx.author.id}")

        await self.bot.db.users.update_one(
            {"user_id": target.id},
            {"$set": {"mastery": amount}},
            upsert=True
        )
        embed = success_embed(
            "📖 Mastery Set",
            f"Mastery set to {amount}% for {target.name}."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="setcombat")
    async def setcombat(self, ctx, amount: float, member: discord.Member = None):
        """Set a player's Combat Mastery."""
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        target = member or ctx.author
        await log_admin_command(self.bot, ctx, "!setcombat", f"Target: {target.id}, Amount: {amount}")
        print(f"[DEBUG] !setcombat {amount} for {target.id} by {ctx.author.id}")

        await self.bot.db.users.update_one(
            {"user_id": target.id},
            {"$set": {"combat_mastery": amount}},
            upsert=True
        )
        embed = success_embed(
            "⚔️ Combat Mastery Set",
            f"Combat Mastery set to {amount} for {target.name}."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="fixmeridians")
    async def fixmeridians(self, ctx, member: discord.Member = None):
        """Instantly heal a player's meridian damage."""
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        target = member or ctx.author
        await log_admin_command(self.bot, ctx, "!fixmeridians", f"Target: {target.id}")
        print(f"[DEBUG] !fixmeridians {target.id} by {ctx.author.id}")

        await self.bot.db.users.update_one(
            {"user_id": target.id},
            {"$set": {"meridian_damage": None}},
            upsert=True
        )
        embed = success_embed(
            "✨ Heavenly Mend",
            f"{target.name}'s meridians have been restored."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="refill")
    async def refill(self, ctx, member: discord.Member = None):
        """Restore a player's full HP and Vitality."""
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        target = member or ctx.author
        await log_admin_command(self.bot, ctx, "!refill", f"Target: {target.id}")
        print(f"[DEBUG] !refill {target.id} by {ctx.author.id}")

        user = await self.bot.db.users.find_one({"user_id": target.id})
        if not user:
            embed = error_embed("❌ Not Registered", f"{target.name} is not registered.")
            await ctx.send(embed=embed, delete_after=2)
            return

        rank = user.get("rank", "The Bound (Mortal)")
        caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 300, "Second-Rate Warrior": 600}
        max_v = caps.get(rank, 1000)

        await self.bot.db.users.update_one(
            {"user_id": target.id},
            {"$set": {"vitality": max_v, "hp": max_v}}
        )
        embed = success_embed(
            "🍷 Divine Favor",
            f"{target.name} restored to {max_v} Vitality/HP."
        )
        await ctx.send(embed=embed, delete_after=2)

    # ==========================================
    # BAN / UNBAN COMMANDS
    # Requires system permission
    # ==========================================

    @commands.command(name="ban")
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a user from using the bot."""
        if not await has_permission(self.bot, ctx.author.id, "system"):
            embed = permission_denied_embed("system")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!ban", f"Target: {member.id}, Reason: {reason}")

        # Check if already banned
        existing = await self.bot.db.banned_users.find_one({"user_id": member.id})
        if existing:
            embed = error_embed("❌ Already Banned", f"{member.mention} is already banned.")
            await ctx.send(embed=embed, delete_after=2)
            return

        now = datetime.datetime.now().isoformat()
        await self.bot.db.banned_users.insert_one({
            "user_id": member.id,
            "reason": reason,
            "banned_at": now,
            "banned_by": ctx.author.id
        })

        print(f"[DEBUG] !ban {member.id} by {ctx.author.id}, reason: {reason}")
        embed = success_embed(
            "🔨 User Banned",
            f"**Banned:** {member.mention}\n**Reason:** {reason}"
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="unban")
    async def unban(self, ctx, member: discord.Member):
        """Unban a user, allowing them to use the bot again."""
        if not await has_permission(self.bot, ctx.author.id, "system"):
            embed = permission_denied_embed("system")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!unban", f"Target: {member.id}")

        result = await self.bot.db.banned_users.delete_one({"user_id": member.id})
        if result.deleted_count == 0:
            embed = error_embed("❌ Not Banned", f"{member.mention} is not banned.")
            await ctx.send(embed=embed, delete_after=2)
            return

        print(f"[DEBUG] !unban {member.id} by {ctx.author.id}")
        embed = success_embed("✅ User Unbanned", f"{member.mention} can now use the bot again.")
        await ctx.send(embed=embed, delete_after=2)

    # ==========================================
    # CONFIGURATION COMMANDS
    # Requires config_manage permission
    # ==========================================

    @commands.command(name="toggle")
    async def toggle(self, ctx, feature: str):
        """Enable or disable a bot feature."""
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            embed = permission_denied_embed("config_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!toggle", f"Feature: {feature}")

        valid_features = ["pvp", "professions", "bazaar", "afk_gains", "combat", "cultivation", "items", "pavilion"]
        if feature.lower() not in valid_features:
            embed = error_embed(
                "❌ Invalid Feature",
                f"Choose from: {', '.join(valid_features)}"
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        key = f"toggle_{feature.lower()}"
        current = await get_setting(self.bot, key, True)
        new_value = not current
        await set_setting(self.bot, key, new_value)

        status = "enabled" if new_value else "disabled"
        print(f"[DEBUG] !toggle {feature} -> {status} by {ctx.author.id}")

        embed = success_embed(
            "⚙️ Feature Toggled",
            f"{feature.capitalize()} is now **{status}**."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="set_cooldown")
    async def set_cooldown(self, ctx, command: str, seconds: int):
        """Change the cooldown for a specific command."""
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            embed = permission_denied_embed("config_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!set_cooldown", f"Command: {command}, Seconds: {seconds}")

        valid_commands = ["work", "observe", "hunt", "recover", "focus", "rest", "breakthrough", "spar"]
        if command.lower() not in valid_commands:
            embed = error_embed(
                "❌ Invalid Command",
                f"Choose from: {', '.join(valid_commands)}"
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        key = f"cooldown_{command.lower()}"
        await set_setting(self.bot, key, seconds)

        print(f"[DEBUG] !set_cooldown {command} -> {seconds}s by {ctx.author.id}")
        embed = success_embed(
            "⏳ Cooldown Updated",
            f"Cooldown for `!{command}` set to **{seconds} seconds**."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="set_emoji")
    async def set_emoji(self, ctx, name: str, emoji: str):
        """Change the emoji used for a specific stat or action."""
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            embed = permission_denied_embed("config_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!set_emoji", f"Name: {name}, Emoji: {emoji}")

        valid_names = ["ki", "tael", "hp", "vitality", "mastery", "combat", "meditate", "work", "observe", "breakthrough", "success", "failure", "cooldown"]
        if name.lower() not in valid_names:
            embed = error_embed(
                "❌ Invalid Emoji Name",
                f"Choose from: {', '.join(valid_names)}"
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        key = f"emoji_{name.lower()}"
        await set_setting(self.bot, key, emoji)

        print(f"[DEBUG] !set_emoji {name} -> {emoji} by {ctx.author.id}")
        embed = success_embed(
            "✅ Emoji Updated",
            f"Emoji `{name}` set to {emoji}."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="set_message")
    async def set_message(self, ctx, key: str, *, text: str):
        """Change a bot response message."""
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            embed = permission_denied_embed("config_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!set_message", f"Key: {key}")

        valid_keys = ["not_registered", "meridian_damage", "cooldown", "no_ki", "no_vitality", 
                     "already_meditating", "not_meditating", "cancelled", "recover_complete", 
                     "focus_complete", "rest_complete"]
        if key.lower() not in valid_keys:
            embed = error_embed(
                "❌ Invalid Message Key",
                f"Choose from: {', '.join(valid_keys)}"
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        db_key = f"msg_{key.lower()}"
        await set_setting(self.bot, db_key, text)

        print(f"[DEBUG] !set_message {key} -> {text[:50]}... by {ctx.author.id}")
        embed = success_embed(
            "✅ Message Updated",
            f"Message `{key}` has been updated."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="debug")
    async def debug(self, ctx, state: str):
        """Toggle debug mode on or off."""
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            embed = permission_denied_embed("config_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!debug", f"State: {state}")

        if state.lower() not in ["on", "off"]:
            embed = error_embed("❌ Invalid State", "Use `!debug on` or `!debug off`.")
            await ctx.send(embed=embed, delete_after=2)
            return

        new_value = state.lower() == "on"
        await set_setting(self.bot, "debug_mode", new_value)

        print(f"[DEBUG] !debug {state} by {ctx.author.id}")
        embed = success_embed(
            "🔍 Debug Mode",
            f"Debug mode is now **{state.upper()}**."
        )
        await ctx.send(embed=embed, delete_after=2)

    @commands.command(name="settings")
    async def settings(self, ctx):
        """View all current bot settings."""
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            embed = permission_denied_embed("config_manage")
            await ctx.send(embed=embed, delete_after=2)
            return

        await ctx.message.delete()

        toggles = {}
        cooldowns = {}
        emojis = {}
        messages = {}

        # Fetch all settings from bot_settings collection
        cursor = self.bot.db.bot_settings.find({})
        async for doc in cursor:
            key = doc.get("setting_key")
            value = doc.get("setting_value")
            if key.startswith("toggle_"):
                toggles[key[7:]] = value
            elif key.startswith("cooldown_"):
                cooldowns[key[9:]] = value
            elif key.startswith("emoji_"):
                emojis[key[6:]] = value
            elif key.startswith("msg_"):
                messages[key[4:]] = value

        embed = settings_embed(toggles, cooldowns, emojis, messages)
        await ctx.send(embed=embed, delete_after=30)

    # ==========================================
    # NEW ADMIN INVENTORY COMMANDS (Without Embeds)
    # ==========================================

    @commands.command(name="inspect")
    async def admin_inspect(self, ctx, member: discord.Member):
        """
        View a player's inventory.
        
        Usage: !inspect @user
        Requires: player_manage permission
        """
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return
        
        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!inspect", f"Target: {member.id}")
        
        # Get inventory
        inventory = await self.bot.db.get_inventory(member.id)
        inventory_text = await format_inventory_for_admin(inventory)
        
        # Use embed from admin_embeds.py
        embed = inventory_inspect_embed(member, inventory_text)
        await ctx.send(embed=embed, delete_after=30)

    @commands.command(name="removeitem")
    async def admin_remove_item(self, ctx, member: discord.Member, item_name: str, quantity: int = 1):
        """
        Remove an item from a player's inventory.
        
        Usage: !removeitem @user "Item Name" [quantity]
        Requires: player_manage permission
        """
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            embed = permission_denied_embed("player_manage")
            await ctx.send(embed=embed, delete_after=2)
            return
        
        await ctx.message.delete()
        await log_admin_command(self.bot, ctx, "!removeitem", f"Target: {member.id}, Item: {item_name}, Qty: {quantity}")
        
        # Check if player has the item
        has_it = await self.bot.db.has_item(member.id, item_name, quantity)
        if not has_it:
            embed = error_embed(
                "❌ Item Not Found",
                f"{member.display_name} does not have {quantity}x {item_name}"
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        # Remove the item
        await self.bot.db.remove_item(member.id, item_name, quantity)
        
        # Use embed from admin_embeds.py
        embed = item_removed_embed(member, item_name, quantity)
        await ctx.send(embed=embed, delete_after=5)

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Admin(bot))
    print("[DEBUG] commands/admin.py: Setup complete")
