import discord
from discord.ext import commands
import asyncio
import datetime

PERMANENT_GOD = 756012403291848804 
temporary_gods = set() 

# ==========================================
# HELPER: Get setting from database
# ==========================================
async def get_setting(bot, key, default=None):
    try:
        async with bot.db.execute("SELECT setting_value FROM bot_settings WHERE setting_key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                val = row[0]
                if val.isdigit():
                    return int(val)
                if val.lower() in ('true', 'false'):
                    return val.lower() == 'true'
                return val
    except:
        pass
    return default

async def set_setting(bot, key, value):
    try:
        await bot.db.execute(
            "INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, str(value))
        )
        await bot.db.commit()
        return True
    except:
        return False

# ==========================================
# PERMISSION HELPERS
# ==========================================
async def has_permission(bot, user_id, permission):
    if user_id == PERMANENT_GOD:
        return True
    if user_id in temporary_gods:
        return True
    try:
        async with bot.db.execute("SELECT 1 FROM admin_permissions WHERE user_id = ? AND permission = ?", (user_id, permission)) as cursor:
            return await cursor.fetchone() is not None
    except:
        return False

async def add_permission(bot, user_id, permission):
    try:
        await bot.db.execute("INSERT OR IGNORE INTO admin_permissions (user_id, permission) VALUES (?, ?)", (user_id, permission))
        await bot.db.commit()
        return True
    except:
        return False

async def remove_permission(bot, user_id, permission):
    try:
        await bot.db.execute("DELETE FROM admin_permissions WHERE user_id = ? AND permission = ?", (user_id, permission))
        await bot.db.commit()
        return True
    except:
        return False

async def get_user_permissions(bot, user_id):
    try:
        async with bot.db.execute("SELECT permission FROM admin_permissions WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    except:
        return []

# ==========================================
# ADMIN COG
# ==========================================
class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Admin cog loaded")

    # ==========================================
    # PERMISSION MANAGEMENT COMMANDS
    # ==========================================
    @commands.command()
    async def allow(self, ctx, member: discord.Member, permission: str):
        if ctx.author.id != PERMANENT_GOD:
            await ctx.send("❌ Only the Permanent God can grant permissions.", delete_after=5)
            return
        await ctx.message.delete()
        
        valid_perms = ["player_manage", "config_manage", "system", "all"]
        if permission.lower() not in valid_perms:
            await ctx.send(f"❌ Invalid permission. Choose from: {', '.join(valid_perms)}", delete_after=10)
            return
        
        if permission.lower() == "all":
            for perm in ["player_manage", "config_manage", "system"]:
                await add_permission(self.bot, member.id, perm)
            await ctx.send(f"✅ {member.mention} granted **ALL** permissions.", delete_after=5)
        else:
            await add_permission(self.bot, member.id, permission.lower())
            await ctx.send(f"✅ {member.mention} granted `{permission}` permission.", delete_after=5)
        
        print(f"[DEBUG] !allow {member.id} {permission} by {ctx.author.id}")

    @commands.command()
    async def deny(self, ctx, member: discord.Member, permission: str):
        if ctx.author.id != PERMANENT_GOD:
            await ctx.send("❌ Only the Permanent God can remove permissions.", delete_after=5)
            return
        await ctx.message.delete()
        
        valid_perms = ["player_manage", "config_manage", "system", "all"]
        if permission.lower() not in valid_perms:
            await ctx.send(f"❌ Invalid permission. Choose from: {', '.join(valid_perms)}", delete_after=10)
            return
        
        if permission.lower() == "all":
            for perm in ["player_manage", "config_manage", "system"]:
                await remove_permission(self.bot, member.id, perm)
            await ctx.send(f"✅ Removed **ALL** permissions from {member.mention}.", delete_after=5)
        else:
            await remove_permission(self.bot, member.id, permission.lower())
            await ctx.send(f"✅ Removed `{permission}` permission from {member.mention}.", delete_after=5)
        
        print(f"[DEBUG] !deny {member.id} {permission} by {ctx.author.id}")

    @commands.command()
    async def perms(self, ctx, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "system"):
            if ctx.author.id != PERMANENT_GOD:
                await ctx.send("❌ You don't have permission to view permissions.", delete_after=5)
                return
        await ctx.message.delete()
        
        target = member or ctx.author
        perms = await get_user_permissions(self.bot, target.id)
        
        if target.id == PERMANENT_GOD:
            perm_list = "👑 **Permanent God** – all permissions"
        elif target.id in temporary_gods:
            perm_list = "🌟 **Temporary God** – all permissions (via !promote)"
        elif perms:
            perm_list = "\n".join([f"• {p}" for p in perms])
        else:
            perm_list = "❌ No permissions"
        
        embed = discord.Embed(title=f"Permissions for {target.name}", color=0x00AAFF)
        embed.description = perm_list
        await ctx.send(embed=embed, delete_after=15)

    # ==========================================
    # SYNC COMMAND
    # ==========================================
    @commands.command()
    async def sync(self, ctx):
        if not await has_permission(self.bot, ctx.author.id, "system"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        print(f"[DEBUG] !sync used by {ctx.author.id}")
        await ctx.send("📡 Syncing with the heavens...")
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Success! **{len(synced)}** commands registered to the `/` menu.")
        except Exception as e:
            await ctx.send(f"❌ Sync failed: {e}")

    # ==========================================
    # DIVINE (Admin help menu)
    # ==========================================
    @commands.command()
    async def divine(self, ctx):
        user_id = ctx.author.id
        await ctx.message.delete()
        print(f"[DEBUG] !divine used by {user_id}")
        
        has_player = await has_permission(self.bot, user_id, "player_manage") or user_id == PERMANENT_GOD or user_id in temporary_gods
        has_config = await has_permission(self.bot, user_id, "config_manage") or user_id == PERMANENT_GOD or user_id in temporary_gods
        has_system = await has_permission(self.bot, user_id, "system") or user_id == PERMANENT_GOD or user_id in temporary_gods
        
        embed = discord.Embed(title="⚡ The Divine Scroll", color=0xFFD700)
        description = ""
        
        if has_player:
            description += "**👤 Player Management:**\n"
            description += "`!reset @user` - Erase a player\n"
            description += "`!setki <num> @user` - Set Ki levels\n"
            description += "`!settaels <num> @user` - Set Tael amount\n"
            description += "`!setmastery <num> @user` - Set Technique Mastery\n"
            description += "`!setcombat <num> @user` - Set Combat Mastery\n"
            description += "`!fixmeridians @user` - Instant Heal Debuff\n"
            description += "`!refill @user` - Full HP/Vit restoration\n\n"
        
        if has_config:
            description += "**⚙️ Configuration Commands:**\n"
            description += "`!toggle <feature>` - Turn features on/off\n"
            description += "`!set_cooldown <cmd> <sec>` - Change command cooldown\n"
            description += "`!set_emoji <name> <emoji>` - Change bot emojis\n"
            description += "`!set_message <key> <text>` - Change bot messages\n"
            description += "`!debug <on/off>` - Toggle debug mode\n"
            description += "`!settings` - View all current settings\n\n"
        
        if has_system:
            description += "**🔧 System:**\n"
            description += "`!sync` - Register Slash Commands\n"
            description += "`!pulse` - Force Recovery Heartbeat\n"
            description += "`!promote @user` - Grant God Powers\n"
            description += "`!demote @user` - Strip God Powers\n"
            description += "`!allow @user <perm>` - Grant permissions\n"
            description += "`!deny @user <perm>` - Remove permissions\n"
            description += "`!perms @user` - View permissions\n"
            description += "`!ban @user <reason>` - Ban user from bot\n"
            description += "`!unban @user` - Unban user\n"
        
        if not description:
            description = "❌ You have no admin permissions."
        
        embed.description = description
        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ Open your DMs to receive the scroll.", delete_after=5)

    # ==========================================
    # DIVINE PULSE
    # ==========================================
    @commands.command()
    async def pulse(self, ctx):
        if not await has_permission(self.bot, ctx.author.id, "system"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        print(f"[DEBUG] !pulse used by {ctx.author.id}")
        mechanics_cog = self.bot.get_cog('Mechanics')
        if mechanics_cog:
            await mechanics_cog.heartbeat()
            await ctx.send("🌀 **Divine Pulse:** Recovery triggered.", delete_after=5)

    # ==========================================
    # USER MANAGEMENT
    # ==========================================
    @commands.command()
    async def promote(self, ctx, member: discord.Member):
        if ctx.author.id != PERMANENT_GOD:
            await ctx.send("❌ Only the Permanent God can promote.", delete_after=5)
            return
        await ctx.message.delete()
        temporary_gods.add(member.id)
        print(f"[DEBUG] !promote {member.id} by {ctx.author.id}")
        await ctx.send(f"🌟 {member.mention} promoted to Temporary God.", delete_after=5)

    @commands.command()
    async def demote(self, ctx, member: discord.Member):
        if ctx.author.id != PERMANENT_GOD:
            await ctx.send("❌ Only the Permanent God can demote.", delete_after=5)
            return
        await ctx.message.delete()
        if member.id in temporary_gods:
            temporary_gods.remove(member.id)
            print(f"[DEBUG] !demote {member.id} by {ctx.author.id}")
            await ctx.send(f"💢 {member.mention} stripped of Divine Power.", delete_after=5)
        else:
            await ctx.send(f"❌ {member.mention} is not a God.", delete_after=5)

    # ==========================================
    # PLAYER MANAGEMENT (requires player_manage)
    # ==========================================
    @commands.command()
    async def reset(self, ctx, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        target = member or ctx.author
        print(f"[DEBUG] !reset {target.id} by {ctx.author.id}")
        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", (target.id,))
        await self.bot.db.commit()
        await ctx.send(f"♻️ **Divine Reset:** {target.name} erased from history.", delete_after=5)

    @commands.command()
    async def setki(self, ctx, amount: int, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        target = member or ctx.author
        print(f"[DEBUG] !setki {amount} for {target.id} by {ctx.author.id}")
        await self.bot.db.execute("UPDATE users SET ki = ? WHERE user_id = ?", (amount, target.id))
        await self.bot.db.commit()
        await ctx.send(f"✨ Ki set to {amount} for {target.name}.", delete_after=5)

    @commands.command()
    async def settaels(self, ctx, amount: int, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        target = member or ctx.author
        print(f"[DEBUG] !settaels {amount} for {target.id} by {ctx.author.id}")
        await self.bot.db.execute("UPDATE users SET taels = ? WHERE user_id = ?", (amount, target.id))
        await self.bot.db.commit()
        await ctx.send(f"💰 Taels set to {amount} for {target.name}.", delete_after=5)

    @commands.command()
    async def setmastery(self, ctx, amount: float, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        target = member or ctx.author
        print(f"[DEBUG] !setmastery {amount} for {target.id} by {ctx.author.id}")
        await self.bot.db.execute("UPDATE users SET mastery = ? WHERE user_id = ?", (amount, target.id))
        await self.bot.db.commit()
        await ctx.send(f"📖 Mastery set to {amount}% for {target.name}.", delete_after=5)

    @commands.command()
    async def setcombat(self, ctx, amount: float, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        target = member or ctx.author
        print(f"[DEBUG] !setcombat {amount} for {target.id} by {ctx.author.id}")
        await self.bot.db.execute("UPDATE users SET combat_mastery = ? WHERE user_id = ?", (amount, target.id))
        await self.bot.db.commit()
        await ctx.send(f"⚔️ Combat Mastery set to {amount} for {target.name}.", delete_after=5)

    @commands.command()
    async def fixmeridians(self, ctx, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        target = member or ctx.author
        print(f"[DEBUG] !fixmeridians {target.id} by {ctx.author.id}")
        await self.bot.db.execute("UPDATE users SET meridian_damage = NULL WHERE user_id = ?", (target.id,))
        await self.bot.db.commit()
        await ctx.send(f"✨ **Heavenly Mend:** {target.name}'s meridians have been restored.", delete_after=5)

    @commands.command()
    async def refill(self, ctx, member: discord.Member = None):
        if not await has_permission(self.bot, ctx.author.id, "player_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        target = member or ctx.author
        print(f"[DEBUG] !refill {target.id} by {ctx.author.id}")
        
        async with self.bot.db.execute("SELECT rank FROM users WHERE user_id = ?", (target.id,)) as cursor:
            user = await cursor.fetchone()
        if not user:
            await ctx.send(f"❌ {target.name} is not registered.", delete_after=5)
            return

        rank = user[0]
        caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 300, "Second-Rate Warrior": 600}
        max_v = caps.get(rank, 1000)

        await self.bot.db.execute("UPDATE users SET vitality = ?, hp = ? WHERE user_id = ?", (max_v, max_v, target.id))
        await self.bot.db.commit()
        await ctx.send(f"🍷 **Divine Favor:** {target.name} restored to {max_v} Vitality.", delete_after=5)

    # ==========================================
    # BAN / UNBAN COMMANDS
    # ==========================================
    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if not await has_permission(self.bot, ctx.author.id, "system"):
            await ctx.send("❌ You don't have permission to ban users.", delete_after=5)
            return
        await ctx.message.delete()
        
        async with self.bot.db.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (member.id,)) as cursor:
            if await cursor.fetchone():
                await ctx.send(f"❌ {member.mention} is already banned.", delete_after=5)
                return
        
        now = datetime.datetime.now().isoformat()
        await self.bot.db.execute(
            "INSERT INTO banned_users (user_id, reason, banned_at, banned_by) VALUES (?, ?, ?, ?)",
            (member.id, reason, now, ctx.author.id)
        )
        await self.bot.db.commit()
        
        print(f"[DEBUG] !ban {member.id} by {ctx.author.id}, reason: {reason}")
        await ctx.send(f"🔨 **Banned** {member.mention}\nReason: {reason}", delete_after=5)

    @commands.command()
    async def unban(self, ctx, member: discord.Member):
        if not await has_permission(self.bot, ctx.author.id, "system"):
            await ctx.send("❌ You don't have permission to unban users.", delete_after=5)
            return
        await ctx.message.delete()
        
        async with self.bot.db.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (member.id,)) as cursor:
            if not await cursor.fetchone():
                await ctx.send(f"❌ {member.mention} is not banned.", delete_after=5)
                return
        
        await self.bot.db.execute("DELETE FROM banned_users WHERE user_id = ?", (member.id,))
        await self.bot.db.commit()
        
        print(f"[DEBUG] !unban {member.id} by {ctx.author.id}")
        await ctx.send(f"✅ **Unbanned** {member.mention}", delete_after=5)

    # ==========================================
    # CONFIGURATION COMMANDS (require config_manage)
    # ==========================================
    @commands.command()
    async def toggle(self, ctx, feature: str):
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        
        valid_features = ["pvp", "professions", "bazaar", "afk_gains", "combat", "cultivation", "items", "pavilion"]
        if feature.lower() not in valid_features:
            await ctx.send(f"❌ Invalid feature. Choose from: {', '.join(valid_features)}", delete_after=10)
            return
        
        key = f"toggle_{feature.lower()}"
        current = await get_setting(self.bot, key, True)
        new_value = not current
        await set_setting(self.bot, key, new_value)
        
        status = "enabled" if new_value else "disabled"
        print(f"[DEBUG] !toggle {feature} -> {status} by {ctx.author.id}")
        await ctx.send(f"✅ {feature.capitalize()} is now **{status}**.", delete_after=5)

    @commands.command()
    async def set_cooldown(self, ctx, command: str, seconds: int):
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        
        valid_commands = ["work", "observe", "hunt", "recover", "focus", "rest", "breakthrough", "spar"]
        if command.lower() not in valid_commands:
            await ctx.send(f"❌ Invalid command. Choose from: {', '.join(valid_commands)}", delete_after=10)
            return
        
        key = f"cooldown_{command.lower()}"
        await set_setting(self.bot, key, seconds)
        
        print(f"[DEBUG] !set_cooldown {command} -> {seconds}s by {ctx.author.id}")
        await ctx.send(f"⏳ Cooldown for `!{command}` set to **{seconds} seconds**.", delete_after=5)

    @commands.command()
    async def set_emoji(self, ctx, name: str, emoji: str):
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        
        valid_names = ["ki", "tael", "hp", "vitality", "mastery", "combat", "meditate", "work", "observe", "breakthrough", "success", "failure", "cooldown"]
        if name.lower() not in valid_names:
            await ctx.send(f"❌ Invalid emoji name. Choose from: {', '.join(valid_names)}", delete_after=10)
            return
        
        key = f"emoji_{name.lower()}"
        await set_setting(self.bot, key, emoji)
        
        print(f"[DEBUG] !set_emoji {name} -> {emoji} by {ctx.author.id}")
        await ctx.send(f"✅ Emoji `{name}` set to {emoji}.", delete_after=5)

    @commands.command()
    async def set_message(self, ctx, key: str, *, text: str):
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        
        valid_keys = ["not_registered", "meridian_damage", "cooldown", "no_ki", "no_vitality", 
                     "already_meditating", "not_meditating", "cancelled", "recover_complete", "focus_complete", "rest_complete"]
        if key.lower() not in valid_keys:
            await ctx.send(f"❌ Invalid message key. Choose from: {', '.join(valid_keys)}", delete_after=10)
            return
        
        db_key = f"msg_{key.lower()}"
        await set_setting(self.bot, db_key, text)
        
        print(f"[DEBUG] !set_message {key} -> {text[:50]}... by {ctx.author.id}")
        await ctx.send(f"✅ Message `{key}` updated.", delete_after=5)

    @commands.command()
    async def debug(self, ctx, state: str):
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        
        if state.lower() not in ["on", "off"]:
            await ctx.send("❌ Use `!debug on` or `!debug off`.", delete_after=5)
            return
        
        new_value = state.lower() == "on"
        await set_setting(self.bot, "debug_mode", new_value)
        
        print(f"[DEBUG] !debug {state} by {ctx.author.id}")
        await ctx.send(f"🔍 Debug mode is now **{state.upper()}**.", delete_after=5)

    @commands.command()
    async def settings(self, ctx):
        if not await has_permission(self.bot, ctx.author.id, "config_manage"):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return
        await ctx.message.delete()
        
        toggles = {}
        cooldowns = {}
        emojis = {}
        messages = {}
        
        async with self.bot.db.execute("SELECT setting_key, setting_value FROM bot_settings") as cursor:
            rows = await cursor.fetchall()
            for key, value in rows:
                if key.startswith("toggle_"):
                    toggles[key[7:]] = value
                elif key.startswith("cooldown_"):
                    cooldowns[key[9:]] = value
                elif key.startswith("emoji_"):
                    emojis[key[6:]] = value
                elif key.startswith("msg_"):
                    messages[key[4:]] = value
        
        embed = discord.Embed(title="⚙️ Current Bot Settings", color=0x00AAFF)
        
        if toggles:
            toggle_text = "\n".join([f"• {k}: {'✅' if v == 'True' else '❌'}" for k, v in toggles.items()])
            embed.add_field(name="Feature Toggles", value=toggle_text, inline=False)
        
        if cooldowns:
            cd_text = "\n".join([f"• !{k}: {v}s" for k, v in cooldowns.items()])
            embed.add_field(name="Cooldowns", value=cd_text, inline=False)
        
        if emojis:
            emoji_text = "\n".join([f"• {k}: {v}" for k, v in emojis.items()])
            embed.add_field(name="Emojis", value=emoji_text, inline=False)
        
        if messages:
            msg_text = "\n".join([f"• {k}: {v[:50]}..." for k, v in messages.items()])
            embed.add_field(name="Messages (preview)", value=msg_text, inline=False)
        
        await ctx.send(embed=embed, delete_after=30)

async def setup(bot):
    await bot.add_cog(Admin(bot))