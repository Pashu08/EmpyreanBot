import datetime
import functools
from discord.ext import commands
from utils import db as db_utils
import config

# ==========================================
# HELPER: Get setting from database
# ==========================================
async def _get_setting(bot, key, default=None):
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

# ==========================================
# 1. REGISTERED CHECK
# ==========================================
def registered():
    """Command guard: rejects if player hasn't used !start."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.registered: Checking user {ctx.author.id}")
        if not await db_utils.user_exists(ctx.bot.db, ctx.author.id):
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 2. NOT MEDITATING
# ==========================================
def not_meditating():
    """Rejects if player is in active meditation."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.not_meditating: Checking user {ctx.author.id}")
        if hasattr(ctx.bot, 'is_meditating') and ctx.author.id in ctx.bot.is_meditating:
            msg = await _get_setting(ctx.bot, "msg_already_meditating", config.MSG_ALREADY_MEDITATING)
            await ctx.send(msg, ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 3. MERIDIANS INTACT
# ==========================================
def meridians_intact():
    """Rejects if player has damaged meridians."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.meridians_intact: Checking user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if user and user.get('meridian_damage'):
            try:
                exp = datetime.datetime.fromisoformat(user['meridian_damage'])
                if datetime.datetime.now() < exp:
                    diff = exp - datetime.datetime.now()
                    minutes = int(diff.total_seconds() // 60)
                    msg = await _get_setting(ctx.bot, "msg_meridian_damage", config.MSG_MERIDIAN_DAMAGE)
                    await ctx.send(msg.format(minutes=minutes), ephemeral=True)
                    return False
            except (ValueError, TypeError):
                pass
        return True
    return commands.check(predicate)

# ==========================================
# 4. NOT IN COMBAT
# ==========================================
def not_in_combat():
    """Rejects if player is currently in a hunt (has CombatView open)."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.not_in_combat: Checking user {ctx.author.id}")
        # Check if user has an active combat view stored in bot memory
        if hasattr(ctx.bot, 'active_combats') and ctx.author.id in ctx.bot.active_combats:
            await ctx.send("❌ You are already in combat! Finish your current fight first.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 5. COOLDOWN CHECK (from bot_settings)
# ==========================================
def cooldown_check(command_name):
    """Reads cooldown from bot_settings table instead of hardcoded."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.cooldown_check: Checking {command_name} for user {ctx.author.id}")
        cooldown_key = f"cooldown_{command_name}"
        seconds = await _get_setting(ctx.bot, cooldown_key, None)
        if seconds is None:
            return True  # No cooldown set, allow command
        # Check if user has a cooldown tracker
        if not hasattr(ctx.bot, 'command_cooldowns'):
            ctx.bot.command_cooldowns = {}
        user_key = f"{command_name}_{ctx.author.id}"
        last_used = ctx.bot.command_cooldowns.get(user_key, 0)
        now = datetime.datetime.now().timestamp()
        if now - last_used < seconds:
            remaining = int(seconds - (now - last_used))
            msg = await _get_setting(ctx.bot, "msg_cooldown", config.MSG_COOLDOWN)
            await ctx.send(msg.format(seconds=remaining), ephemeral=True)
            return False
        ctx.bot.command_cooldowns[user_key] = now
        return True
    return commands.check(predicate)

# ==========================================
# 6. HAS ENOUGH KI
# ==========================================
def has_enough_ki(amount):
    """Checks if player has at least 'amount' Ki."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.has_enough_ki: Need {amount} for user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if not user:
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        current_ki = user.get('ki', 0)
        if current_ki < amount:
            msg = await _get_setting(ctx.bot, "msg_no_ki", config.MSG_NO_KI)
            await ctx.send(msg.format(required=amount), ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 7. HAS ENOUGH VITALITY
# ==========================================
def has_enough_vitality(amount):
    """Checks if player has at least 'amount' Vitality."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.has_enough_vitality: Need {amount} for user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if not user:
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        current_vit = user.get('vitality', 0)
        if current_vit < amount:
            msg = await _get_setting(ctx.bot, "msg_no_vitality", config.MSG_NO_VITALITY)
            await ctx.send(msg.format(required=amount), ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 8. MINIMUM RANK
# ==========================================
def min_rank(required_rank):
    """Checks if player's rank is at least the required rank."""
    rank_order = [
        "The Bound (Mortal)",
        "Third-Rate Warrior",
        "Second-Rate Warrior",
        "First-Rate Warrior",
        "Peak Master"
    ]
    async def predicate(ctx):
        print(f"[DEBUG] checks.min_rank: Need {required_rank} for user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if not user:
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        current_rank = user.get('rank', "The Bound (Mortal)")
        if rank_order.index(current_rank) < rank_order.index(required_rank):
            await ctx.send(f"❌ You need to be at least **{required_rank}** to use this command.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 9. NOT BANNED
# ==========================================
def not_banned():
    """Checks if user is not in the banned_users table."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.not_banned: Checking user {ctx.author.id}")
        try:
            async with ctx.bot.db.execute("SELECT reason FROM banned_users WHERE user_id = ?", (ctx.author.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    reason = row[0]
                    await ctx.send(f"❌ You are banned from using this bot. Reason: {reason}", ephemeral=True)
                    return False
        except:
            pass
        return True
    return commands.check(predicate)

# ==========================================
# 10. PER-USER COOLDOWN (database backed, survives restart)
# ==========================================
def cooldown_per_user(command_name, seconds):
    """Per-user cooldown stored in database (survives bot restart)."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.cooldown_per_user: Checking {command_name} for user {ctx.author.id}")
        table_name = "user_cooldowns"
        # Ensure table exists (will be created in main.py)
        user_key = f"{command_name}_{ctx.author.id}"
        now = datetime.datetime.now().isoformat()
        
        async with ctx.bot.db.execute(
            "SELECT last_used FROM user_cooldowns WHERE cooldown_key = ?",
            (user_key,)
        ) as cursor:
            row = await cursor.fetchone()
        
        if row:
            last_used = datetime.datetime.fromisoformat(row[0])
            elapsed = (datetime.datetime.now() - last_used).total_seconds()
            if elapsed < seconds:
                remaining = int(seconds - elapsed)
                msg = await _get_setting(ctx.bot, "msg_cooldown", config.MSG_COOLDOWN)
                await ctx.send(msg.format(seconds=remaining), ephemeral=True)
                return False
        
        # Update or insert
        await ctx.bot.db.execute(
            "INSERT OR REPLACE INTO user_cooldowns (cooldown_key, last_used) VALUES (?, ?)",
            (user_key, now)
        )
        await ctx.bot.db.commit()
        return True
    return commands.check(predicate)